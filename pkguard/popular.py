"""
Curated lists of well-known, high-traffic packages used as a reference set
for typosquat / hallucination-lookalike distance checks.
Not exhaustive — meant to catch the most common "close to a famous package" cases.
"""

POPULAR_NPM = {
    "react", "react-dom", "vue", "angular", "express", "lodash", "axios", "moment",
    "webpack", "babel", "typescript", "eslint", "jest", "mocha", "chalk", "commander",
    "chalk", "dotenv", "next", "nuxt", "svelte", "redux", "vuex", "jquery", "underscore",
    "request", "async", "bluebird", "rxjs", "socket.io", "prisma", "sequelize", "mongoose",
    "passport", "bcrypt", "jsonwebtoken", "uuid", "nodemon", "pm2", "cors", "helmet",
    "body-parser", "cookie-parser", "multer", "nodemailer", "puppeteer", "playwright",
    "cheerio", "yargs", "inquirer", "ora", "figlet", "colors", "chokidar", "glob",
    "rimraf", "fs-extra", "cross-env", "concurrently", "husky", "lint-staged",
    "prettier", "styled-components", "classnames", "prop-types", "immer", "zustand",
    "recoil", "formik", "yup", "zod", "graphql", "apollo-client", "date-fns", "dayjs",
    "vite", "rollup", "parcel", "esbuild", "tailwindcss", "postcss", "sass", "less",
}

POPULAR_PYPI = {
    "numpy", "pandas", "requests", "flask", "django", "scipy", "matplotlib", "scikit-learn",
    "tensorflow", "torch", "pytorch", "keras", "pillow", "pytest", "setuptools", "pip",
    "wheel", "boto3", "botocore", "sqlalchemy", "click", "jinja2", "pyyaml", "cryptography",
    "certifi", "urllib3", "idna", "charset-normalizer", "six", "python-dateutil", "attrs",
    "packaging", "colorama", "typing-extensions", "aiohttp", "gunicorn", "celery", "redis",
    "psycopg2", "pymongo", "fastapi", "uvicorn", "pydantic", "starlette", "httpx", "beautifulsoup4",
    "lxml", "selenium", "scrapy", "openpyxl", "xlrd", "tqdm", "rich", "loguru", "black",
    "flake8", "mypy", "isort", "poetry", "virtualenv", "pipenv", "docker", "kubernetes",
    "paramiko", "fabric", "invoke", "pyjwt", "bcrypt", "passlib", "cffi", "protobuf",
    "grpcio", "pyarrow", "dask", "xgboost", "lightgbm", "nltk", "spacy", "gensim",
    "opencv-python", "imageio", "networkx", "sympy", "statsmodels", "plotly", "seaborn",
    "bokeh", "streamlit", "gradio", "openai", "anthropic", "langchain", "transformers",
}


def get_popular_set(ecosystem: str) -> set:
    return POPULAR_NPM if ecosystem == "npm" else POPULAR_PYPI
