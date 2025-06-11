import subprocess
import json

def k8sgpt_analyze_explain(namespace, path, context):
    if namespace != 'all':
        command = ["k8sgpt", "analyze", "--explain", "-o", "json", "--anonymize", f"--namespace={namespace}", "--kubeconfig", path, "--kubecontext", context]
    else:
        command = ["k8sgpt", "analyze", "--explain", "-o", "json", "--anonymize", "--kubeconfig", path, "--kubecontext", context]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    
    except FileNotFoundError:
        return None
    
    except subprocess.CalledProcessError as e:
        return None

def k8sgpt_analyze(namespace, path, context):

    if namespace != 'all':
        command = ["k8sgpt", "analyze", "-o", "json", "--anonymize", f"--namespace={namespace}", "--kubeconfig", path, "--kubecontext", context]
    else:
        command = ["k8sgpt", "analyze", "-o", "json", "--anonymize", "--kubeconfig", path, "--kubecontext", context]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    
    except FileNotFoundError:
        return None
    
    except subprocess.CalledProcessError as e:
        return None
