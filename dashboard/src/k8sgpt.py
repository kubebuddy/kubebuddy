import subprocess
import json

def k8sgpt_analyze_explain():
    command = ["k8sgpt", "analyze", "--explain", "-o", "json", "-a"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error running k8sGPT:", e.stderr)


def k8sgpt_analyze():
    command = ["k8sgpt", "analyze", "-o", "json"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error running k8sGPT:", e.stderr)
