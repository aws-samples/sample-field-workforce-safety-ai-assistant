FROM public.ecr.aws/lambda/python:3.13

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt --target .

# Copy function code
COPY index.py ./

# Command to run the handler
CMD ["index.lambda_handler"]
