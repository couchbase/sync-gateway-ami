
# Setup virtual env
virtualenv -p python venv
source venv/bin/activate

# Install python dependencies
pip install -r requirements.txt

# set python env
export PYTHONPATH=$PYTHONPATH:`pwd`/src