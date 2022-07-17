FROM public.ecr.aws/lambda/python:3.6

RUN yum install -y git

COPY requirements.txt  .

RUN  pip3 install -r requirements.txt 

ENV PATH="/var/task/bin:${PATH}"
COPY handler.py /var/task
CMD [ "handler.handler" ] 
