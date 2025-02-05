# KubeBuddy 🤘🏻

## Overview

KubeBuddy is a powerful tool for managing and operating Kubernetes clusters. It offers seamless cluster management, real-time statistics, log streaming, and hands-on troubleshooting capabilities, providing users with an efficient way to monitor, maintain, and resolve issues within their Kubernetes environments.

## Prerequisites

- A running Kubernetes cluster
- A `.kube/config` file present on your machine
- Python 3.10 or above installed on your system
- Git installed on your system

## Installation Steps

### 1. Clone the Repository

```sh
git clone https://github.com/thinknyx-technologies-llp/kubebuddy.git
```

### 2. Create a Virtual Environment

```sh
python -m venv kubebuddy_env
```

### 3. Activate the Virtual Environment

- On Windows:
  ```sh
  .\k8s_env\Scripts\activate
  ```
- On Linux/Mac:
  ```sh
  source k8s_env/bin/activate
  ```

### 4. Install Dependencies

```sh
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file in your project directory and add the following variables:

```sh
SUPERUSER_USERNAME=admin
SUPERUSER_PASSWORD=admin
```

Alternatively, you can export these variables directly in your terminal:

```sh
export SUPERUSER_USERNAME=admin
export SUPERUSER_PASSWORD=admin
```

### 6. Apply Database Migrations

```sh
python manage.py makemigrations
```

If no changes are detected, try:

```sh
python manage.py makemigrations main
```

```sh
python manage.py migrate
```

### 7. Run the Application

```sh
python manage.py runserver
```

## Notes

- You can modify the `SUPERUSER_USERNAME` and `SUPERUSER_PASSWORD` values as needed.
- Ensure your Kubernetes cluster is up and running before executing the steps.
- The `kube/config` file path should be correctly set up to interact with the cluster.

## Contributing

Feel free to fork this repository and submit pull requests with enhancements and bug fixes.

## Powered By

*This project is Powered by [Thinknyx Technologies LLP](www.thinknyx.com)*
