"""Setuptools configuration for the GradCafe Analytics project."""

from setuptools import find_namespace_packages, setup


PY_MODULES = [
    "app",
    "capture_page",
    "clean",
    "load_data",
    "load_original_universities",
    "models",
    "orm_queries",
    "pull_data_workflow",
    "query_data",
    "scrape",
]


setup(
    name="gradcafe-analytics",
    version="5.0.0",
    description=(
        "GradCafe analytics application for the JHU Modern "
        "Software Concepts in Python course."
    ),
    python_requires=">=3.11",
    package_dir={"": "src"},
    py_modules=PY_MODULES,
    packages=find_namespace_packages(
        where="src",
        include=["llm_hosting*"],
    ),
    install_requires=[
        "psycopg[binary]>=3.1,<4",
        "SQLAlchemy>=2.0,<3",
        "Flask>=2.3,<4",
        "beautifulsoup4",
        "websocket-client",
        "requests",
        "huggingface_hub>=0.23.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8",
            "pytest-cov>=5",
            "pylint>=4,<5",
            "pydeps>=3,<4",
            "sphinx>=7",
            "sphinx-rtd-theme>=2",
        ],
    },
)
