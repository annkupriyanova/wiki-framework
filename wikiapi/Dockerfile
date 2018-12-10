FROM python:3.7
EXPOSE 5000

# Sets the working directory for following COPY and CMD instructions
# Notice we haven’t created a directory by this name - this
# instruction creates a directory with this name if it doesn’t exist
WORKDIR /wikiapi

# Install any needed packages specified in requirements.txt
COPY requirements.txt /wikiapi
COPY Galileo_page.txt /wikiapi
RUN pip install -r requirements.txt

# Run app.py when the container launches
COPY api.py /wikiapi
CMD python api.py