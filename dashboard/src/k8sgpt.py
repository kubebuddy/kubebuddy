import subprocess
import json

def k8sgpt_analyze_explain(namespace):
    if namespace != "Select a namespace":
        command = ["k8sgpt", "analyze", "--explain", "-o", "json", "--anonymize", f"--namespace={namespace}"]
    else:
        command = ["k8sgpt", "analyze", "--explain", "-o", "json", "--anonymize"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error running k8sGPT:", e.stderr)


def k8sgpt_analyze(namespace):
    
    if namespace != "Select a namespace":
        command = ["k8sgpt", "analyze", "-o", "json", "--anonymize", f"--namespace={namespace}"]
    else:
        command = ["k8sgpt", "analyze", "-o", "json", "--anonymize"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error running k8sGPT:", e.stderr)
