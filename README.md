# <img src="https://kubebuddy.org/images/logo-hz.png" alt="KubeBuddy Logo" width="400">

![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/kubebuddy/kubebuddy)
![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/kubebuddy/kubebuddy/build.yml)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/kubebuddy/kubebuddy)
[![📘 Documentation](https://img.shields.io/static/v1?label=%F0%9F%93%96&message=Documentation&color=blue)](https://kubebuddy.org/documents/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10%2B-yellow.svg)](https://www.python.org/downloads/release/python-3100/)
![Last Commit](https://img.shields.io/github/last-commit/kubebuddy/kubebuddy/main)
[![Issues](https://img.shields.io/github/issues/kubebuddy/kubebuddy.svg)](https://github.com/kubebuddy/kubebuddy/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/kubebuddy/kubebuddy.svg)](https://github.com/kubebuddy/kubebuddy/pulls)
[![Stars](https://img.shields.io/github/stars/kubebuddy/kubebuddy.svg)](https://github.com/kubebuddy/kubebuddy/stargazers)
[![Forks](https://img.shields.io/github/forks/kubebuddy/kubebuddy.svg)](https://github.com/kubebuddy/kubebuddy/network)

### Code Quality (SonarCloud)

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=kubebuddy_kubebuddy&metric=alert_status)](https://sonarcloud.io/dashboard?id=kubebuddy_kubebuddy)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=kubebuddy_kubebuddy&metric=coverage)](https://sonarcloud.io/dashboard?id=kubebuddy_kubebuddy)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=kubebuddy_kubebuddy&metric=bugs)](https://sonarcloud.io/dashboard?id=kubebuddy_kubebuddy)
[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=kubebuddy_kubebuddy&metric=code_smells)](https://sonarcloud.io/dashboard?id=kubebuddy_kubebuddy)
[![Duplicated Lines](https://sonarcloud.io/api/project_badges/measure?project=kubebuddy_kubebuddy&metric=duplicated_lines_density)](https://sonarcloud.io/dashboard?id=kubebuddy_kubebuddy)



**KubeBuddy** is an AI-powered Kubernetes dashboard tool designed to provide a comprehensive and user-friendly interface for managing Kubernetes clusters. It offers real-time insights & monitoring that makes it easier to track workloads, nodes, and resource usage.

<div align="center">
  <img src="https://github.com/kubebuddy/docs/blob/main/public/kubebuddy.gif?raw=true" width="80%">
</div>

## 🚀 Features

- AI-powered insights for optimal resource allocation
- Multi-cluster support with real-time monitoring
- Clean and interactive UI with role-based access control
- Logs, shell access, and resource editing with documentation
- Interactive visualizations for workload insights

## 📸 Screenshots

<table>
    <tr>
        <td width="33%"><img src="https://github.com/kubebuddy/kubebuddy.github.io/blob/main/images/ss1.png?raw=true"></td>
        <td width="33%"><img src="https://github.com/kubebuddy/kubebuddy.github.io/blob/main/images/ss2.png?raw=true"></td>
    </tr>
    <tr>
        <td width="33%"><img src="https://github.com/kubebuddy/kubebuddy.github.io/blob/main/images/ss3.png?raw=true"></td>
        <td width="33%"><img src="https://github.com/kubebuddy/kubebuddy.github.io/blob/main/images/ss4.png?raw=true"></td>
    </tr>
    <tr>
        <td width="33%"><img src="https://github.com/kubebuddy/kubebuddy.github.io/blob/main/images/ss5.png?raw=true"></td>
        <td width="33%"><img src="https://github.com/kubebuddy/kubebuddy.github.io/blob/main/images/ss6.png?raw=true"></td>
    </tr>
</table>

## 🟢 Quickstart

To install **KubeBuddy** in your system, follow the steps in our [installation guide](https://kubebuddy.org/documents/#installation).

### Accessing the Dashboard

- Ensure you have a valid kubeconfig file configured.
- Run the command below to start the dashboard locally after following the installation steps:

```bash
python manage.py runserver
```

- Access the dashboard via [localhost:8000](http://localhost:8000) or via your https://&lt;public-ip-address&gt;:8000.

## 🤝 Contributing

We welcome contributions from the community! Feel free to fork this repository and submit pull requests with enhancements, bug fixes, or improvements to code quality.

Check out our:

- [Code of Conduct](./code-of-conduct.md)
<!-- - [Contribution Guidelines](https://<add-your-guidelines-link-here>) -->

### 🐞 Improving Code Quality with SonarQube

We use [SonarCloud](https://sonarcloud.io/dashboard?id=kubebuddy_kubebuddy) to continuously analyze the code for issues like bugs, code smells, and coverage gaps. You can contribute by helping us fix reported issues:

👉 [View open issues on SonarCloud](https://sonarcloud.io/project/issues?id=kubebuddy_kubebuddy)

Your contributions not only improve the codebase but also help keep the project healthy and maintainable. ❤️

## 📜 License

This project is licensed under the [Apache 2.0](./LICENSE) license.

## ❓ Frequently Asked Questions

For more information, visit our [FAQ section](https://kubebuddy.org/faqs).

## Powered By

_This project is Powered by [Thinknyx Technologies LLP](www.thinknyx.com)_
