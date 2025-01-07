from django.shortcuts import render
from main.models import KubeConfig
from .src import k8s_pods, k8s_nodes
from django.contrib.auth.decorators import login_required

# Create your views here.
@login_required
def dashboard(request):
    print(KubeConfig.objects.all())
    return render(request, 'dashboard/dashboard.html')

def pods(request):
    pods, pc = k8s_pods.getpods()
    return render(request, 'dashboard/pods.html', { "pods": pods, "pc": pc})

def nodes(request):
    nc, nodes = k8s_nodes.getnodes()
    return render(request, 'dashboard/nodes.html', { "nodes": nodes, "nc": nc})