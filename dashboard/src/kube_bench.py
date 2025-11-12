from kubernetes import client, config
import yaml
import time 
from fpdf import FPDF, XPos, YPos
import re
from datetime import datetime
from .utils import configure_k8s
import os

def run_kube_bench_job(job_file,path, context, namespace="default"):

    configure_k8s(path, context)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    two_levels_up = os.path.dirname(os.path.dirname(BASE_DIR))

    job_path = os.path.join(two_levels_up, 'static', 'fpdf', job_file)
    
    try:
        with open(job_path, "r") as f:
            job_yaml = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Job file {job_file} not found")
        return False
    batch_v1 = client.BatchV1Api()
    job_name = job_yaml["metadata"]["name"]
    try:
        try:
            batch_v1.delete_namespaced_job(
                name=job_name,
                namespace=namespace,
                body=client.V1DeleteOptions(propagation_policy="Background")
            )
            # delete exisitng job
            time.sleep(5)
        except client.rest.ApiException as e:
            if e.status != 404:
                print(f"Warning when deleting existing job: {e}")
        batch_v1.create_namespaced_job(body=job_yaml, namespace=namespace)
        # job submitted
        return job_name
    except client.rest.ApiException as e:
        print(f"❌ Failed to create job: {e}")
        return False

def get_kube_bench_logs(job_name="kube-bench", namespace="default", timeout_seconds=300):
    core_v1 = client.CoreV1Api()
    batch_v1 = client.BatchV1Api()
    start_time = time.time()
    pods = []
    while not pods:
        if time.time() - start_time > timeout_seconds:
            print(f"⚠️ Timeout waiting for pod creation after {timeout_seconds} seconds")
            try:
                job = batch_v1.read_namespaced_job(name=job_name, namespace=namespace)
            except client.rest.ApiException:
                print(f"Job {job_name} not found")
            return None
        pods = core_v1.list_namespaced_pod(
            namespace=namespace,
            label_selector="job-name=" + job_name
        ).items
        if not pods:
            time.sleep(5)
    pod_name = pods[0].metadata.name
    while True:
        if time.time() - start_time > timeout_seconds:
            try:
                log_output = core_v1.read_namespaced_pod_log(name=pod_name, namespace=namespace)
                return log_output
            except Exception as e:
                print(f"Failed to get logs: {e}")
                return None
        try:
            pod = core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            if pod.status.phase in ("Succeeded", "Failed"):
                break
        except Exception as e:
            print(f"Error checking pod status: {e}")
        time.sleep(5)
    try:
        log_output = core_v1.read_namespaced_pod_log(name=pod_name, namespace=namespace)
        return log_output
    except Exception as e:
        print(f"Failed to get logs: {e}")
        return None

class MyPDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Dejavu_Sans', '', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')

def generate_kube_bench_pdf(raw_output, filename="kube_bench_report.pdf", context=None, path=None):
    if isinstance(raw_output, bytes):
        try:
            raw_output = raw_output.decode('utf-8', errors='replace')
        except UnicodeDecodeError:
            raw_output = raw_output.decode('latin-1')
    replacements = {
        ''': "'", ''': "'", '"': '"', '"': '"',
        '\t': '    ',
        '\x80': '', '\x98': '', '\x99': '',
    }
    for bad, good in replacements.items():
        raw_output = raw_output.replace(bad, good)
    sections = parse_kube_bench_output(raw_output)
    pdf = MyPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    two_levels_up = os.path.dirname(os.path.dirname(BASE_DIR))
    font_path = os.path.join(two_levels_up, 'static', 'fpdf', 'DejaVuSans.ttf')
    font_path_bold = os.path.join(two_levels_up, 'static', 'fpdf', 'DejaVuSans-Bold.ttf')
    pdf.add_font('Dejavu_Sans', '', os.path.join(BASE_DIR, 'static', 'fpdf', font_path))
    pdf.add_font('Dejavu_Sans', 'B', os.path.join(BASE_DIR, 'static', 'fpdf', font_path_bold))
    pdf.set_font('Dejavu_Sans', 'B', 16)
    pdf.image(os.path.join(two_levels_up, 'static', 'fpdf', 'logo-hz.png'), x='C', y=None, w=100)
    pdf.cell(0, 10, 'Kubernetes CIS Benchmark Report', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    cluster_name = get_cluster_name(path, context)
    pdf.set_font('Dejavu_Sans', 'B', 12)
    pdf.set_text_color(3, 79, 255)
    pdf.cell(0, 10, cluster_name, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Dejavu_Sans', '', 10)
    pdf.cell(0, 5, f'Date: {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

    # Dynamically construct summary_map based on sections that start with "== Summary"
    summary_map = {}
    summary_index = 1
    for section_title in sections:
        if section_title.startswith("== Summary") and section_title != "== Summary total ==":
            summary_map[str(summary_index)] = section_title
            summary_index += 1
    
    if "== Summary total ==" in sections:
        render_summary_section(pdf, sections["== Summary total =="], "== Summary total ==")
    
    for section_num in ["1", "2", "3", "4", "5"]:
        for section_name, section_content in sections.items():
            if section_name.startswith(section_num + " ") or section_name.startswith(section_num + "."):
                render_section(pdf, section_name, section_content)
        summary_name = summary_map.get(section_num)
        if summary_name and summary_name in sections:
            render_summary_section(pdf, sections[summary_name], summary_name)

    pdf.output(os.path.join(two_levels_up, 'static', 'fpdf', 'kube_bench_report.pdf'))
    # PDF generated

def parse_kube_bench_output(raw_output):
    sections = {}
    summary_pattern = r'== Summary .+? ==\n(.*?)\n\n'
    for match in re.finditer(summary_pattern, raw_output, re.DOTALL):
        section_name = match.group(0).split('\n')[0].strip()
        content = match.group(1).strip()
        sections[section_name] = content
    section_pattern = r'\[INFO\]\s+([\d\.\s]+.*?)(?=\[INFO\]|\Z)'
    for match in re.finditer(section_pattern, raw_output, re.DOTALL):
        section_text = match.group(1).strip()
        if section_text:
            title = section_text.split('\n')[0].strip()
            content = '\n'.join(section_text.split('\n')[1:]).strip()
            sections[title] = content

    return sections

def render_summary_section(pdf, summary_text, summary_title):
    summary_title = summary_title.strip('= ').strip()
    pdf.set_font('Dejavu_Sans', 'B', 12)
    pdf.cell(0, 10, summary_title, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font('Dejavu_Sans', '', 10)
    pdf.set_line_width(0.5)
    table_width = 60 + 40
    page_width = pdf.w - 2 * pdf.l_margin
    x_offset = (page_width - table_width) / 2
    pdf.set_x(pdf.l_margin + x_offset)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(60, 8, 'Status', 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=1)
    pdf.cell(40, 8, 'Count', 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C', fill=1)
    for line in summary_text.split('\n'):
        if re.search(r'PASS|FAIL|WARN|INFO', line):
            status = re.search(r'(PASS|FAIL|WARN|INFO)', line).group(1)
            count = re.search(r'(\d+)', line).group(1)
            pdf.set_x(pdf.l_margin + x_offset)
            if status == 'PASS':
                pdf.set_text_color(0, 128, 0)
            elif status == 'FAIL':
                pdf.set_text_color(255, 0, 0)
            elif status == 'WARN':
                pdf.set_text_color(255, 165, 0)
            else:
                pdf.set_text_color(0, 0, 0)
            pdf.cell(60, 8, status, 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
            pdf.cell(40, 8, count, 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            pdf.set_text_color(0, 0, 0)
    pdf.set_line_width(0.2)
    pdf.cell(0, 3, '', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

def render_section(pdf, section_name, section_content):
    is_subsection = '.' in section_name.split(' ')[0]
    if not is_subsection:
        pdf.cell(0, 10, '', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if is_subsection:
        pdf.set_font('Dejavu_Sans', '', 11)
        pdf.set_fill_color(220, 220, 220)
    else:
        pdf.set_font('Dejavu_Sans', 'B', 12)
        pdf.set_fill_color(200, 200, 200)
    pdf.cell(0, 10, section_name, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=1)
    pdf.cell(0, 2, '', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    lines = section_content.splitlines()
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith("== Summary") or any(keyword in line for keyword in ["checks PASS", "checks FAIL", "checks WARN", "checks INFO"]):
            continue
        cleaned_lines.append(line)
    cleaned_content = '\n'.join(cleaned_lines)
    tests = parse_tests(cleaned_content, section_name)
    for test in tests:
        render_test(pdf, test)
    pdf.cell(0, 5, '', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

def parse_tests(section_content, section_name):
    tests = []
    test_pattern = r'(\[(?:PASS|FAIL|WARN|INFO)\]\s+\d+\.\d+(?:\.\d+)?\s+.*?)(?=\[(?:PASS|FAIL|WARN|INFO)\]\s+\d+\.\d+(?:\.\d+)?\s+|\Z)'
    for match in re.finditer(test_pattern, section_content, re.DOTALL):
        test_text = match.group(1).strip()
        if test_text:
            test_id_match = re.search(r'(\d+\.\d+(?:\.\d+)?)', test_text)
            test_id = test_id_match.group(1) if test_id_match else "Unknown"
            title_match = re.search(r'\d+\.\d+\.\d+\s+(.*?)(?=\[)', test_text)
            title = title_match.group(1).strip() if title_match else "Unknown Test"
            status_match = re.search(r'\[(PASS|FAIL|WARN|INFO)\]', test_text)
            status = status_match.group(1) if status_match else "UNKNOWN"
            details = test_text
            tests.append({
                'id': test_id,
                'title': title,
                'status': status,
                'details': details
            })

    return tests

def render_test(pdf, test):
    pdf.cell(0, 5, '', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Dejavu_Sans', '', 11)
    pdf.cell(17, 5, "Test ID: ", 0, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(15, 5, test['id'], 0, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(15, 5, "Status: ", 0, new_x=XPos.RIGHT, new_y=YPos.TOP)
    if test['status'] == 'PASS':
        pdf.set_text_color(0, 128, 0)
    elif test['status'] == 'FAIL':  
        pdf.set_text_color(255, 0, 0)
    elif test['status'] == 'WARN':
        pdf.set_text_color(255, 165, 0)
    else:
        pdf.set_text_color(0, 0, 0)
    pdf.cell(10, 5, test['status'], 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 3, '', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    clean_details = re.sub(r'\[(PASS|FAIL|WARN|INFO)\]', '', test['details'])
    clean_details = re.sub(rf'^{re.escape(test["id"])}\s*', '', clean_details).strip()

    pdf.set_font('Dejavu_Sans', '', 10)
    pdf.multi_cell(0, 5, clean_details)

def cleanup_kube_bench_job(job_name="kube-bench", namespace="default"):
    batch_v1 = client.BatchV1Api()
    try:
        try:
            batch_v1.read_namespaced_job(name=job_name, namespace=namespace)
            delete_opts = client.V1DeleteOptions(propagation_policy="Background")
            batch_v1.delete_namespaced_job(name=job_name, namespace=namespace, body=delete_opts)
            # cleaned up kube bench job
            return True
        except client.rest.ApiException as e:
            if e.status == 404:
                # could not find
                return True
            else:
                raise e
    except Exception as e:
        print(f"❌ Failed to clean up job: {e}")
        return False

def get_cluster_name(path, context):

    with open(path, 'r') as f:
        kubeconfig = yaml.safe_load(f)

    for ctx in kubeconfig.get('contexts', []):
        if ctx.get('name') == context:
            cluster_name = ctx.get('context', {}).get('cluster')
            return cluster_name

    return None

def get_cluster_server(path, context):
    with open(path, 'r') as f:
        kubeconfig = yaml.safe_load(f)
    
    cluster_name = None
    for ctx in kubeconfig.get('contexts', []):
        if ctx.get('name') == context:
            cluster_name = ctx.get('context', {}).get('cluster')
            break
    
    if not cluster_name:
        raise ValueError(f"Context '{context}' not found in kubeconfig.")

    for cluster in kubeconfig.get('clusters', []):
        if cluster.get('name') == cluster_name:
            return cluster.get('cluster', {}).get('server')

job_name = None

def kube_bench_report_generate(path, context):
    try:
        server = get_cluster_server(path, context)

        if context.startswith('gke_'):
            job_file = 'job-gke.yaml'
        elif context.startswith('arn:aws:eks'):
            job_file = 'job-eks.yaml'
        elif server and 'azmk8s.io' in server: # not correct handling for AKS (WIP)
            job_file = 'job-aks.yaml'
        else:
            job_file = 'job.yaml'

        job_name = run_kube_bench_job(job_file=job_file, path=path, context=context)
        logs = get_kube_bench_logs(job_name=job_name, timeout_seconds=300)
        generate_kube_bench_pdf(logs, filename="kube_bench_report.pdf", context=context, path=path)
    except Exception as e:
        print(f"❌ An error occurred: {e}")
    finally:
        if job_name != None:
            cleanup_kube_bench_job(job_name=job_name)
