from flask import Flask, request, jsonify
from jupyter_server.auth import passwd
from jupyter_server.auth import passwd_check
import logging
import os
import yaml
import re
import json
import shutil
import time
import urllib


class JupyterHelper():
    # Shared functions
    def _get_studies(self):
        """Get information of current studies.

        Input:
            None
        Return:
            - list or None
        """
        studies = []
        search_path = JUPYTER_WORKSPACE

        if not os.path.isdir(search_path):
            msg = 'Path "{}" does not exist.'.format(search_path)
            LOG.error(msg)
            return None

        for user in os.listdir(search_path):
            if not os.path.isdir(os.path.join(search_path, user)):
                continue
            for id in os.listdir(os.path.join(search_path, user)):
                if not id.startswith('benchmark_'):
                    continue
                if os.path.islink(os.path.join(search_path, user, id)):
                    LOG.debug(
                        'Found study "{}" for user "{}".'.format(id, user))
                    studies.append({'id': id, 'user': user})

        return studies

    def _get_labs(self):
        """Get information of the running labs.

        Input:
            None
        Return:
            - list or None
        """
        labs = []

        with os.popen('jupyter server list') as p:
            output = p.readlines()

        # Ex1: 'http://hostname:8888/ :: /app/workspace/cheshi'
        # Ex2: 'http://hostname:8888/?token=b298...d8 :: /app/workspace/cheshi'
        re_labinfo = re.compile(r'^http://(\S+):(\d+)/(\S*) :: (\S+)$')

        try:
            for line in output:
                m = re_labinfo.match(line.strip())
                if m:
                    token = m[3][7:] if m[3].startswith('?token=') else None
                    path = m[4]
                    user = path.split('/')[-1]

                    try:
                        with open(os.path.join(path, '.passwd'), 'r') as f:
                            hash = f.readline()
                    except Exception as err:
                        LOG.warning('Unable to get hashed passwd for user {}. error: {}'.format(
                            user, err))
                        hash = None

                    labs.append({'line': m[0], 'host': m[1], 'port': m[2],
                                 'token': token, 'path': path, 'user': user,
                                 'hash': hash})
        except Exception as err:
            msg = 'Fail to read jupyter server list. error: {}'.format(err)
            LOG.error(msg)
            return None

        return labs

    def _get_lab_by_user(self, username):
        """Get information of the running lab by username.

        Restriction: When the user has multiple labs, only the first one will
        be returned. This may cause problems. But the logic of start lab will
        check the running list, so it will not happen. Only care should be
        taken to prevent users from manually creating labs.

        Input:
            None
        Return:
            - list or None
        """
        labs = self._get_labs()

        if labs is None:
            return None

        for lab in labs:
            if lab['user'] == username:
                return lab

        return None

    def _start_lab(self, username, password):
        """Start a JupyterLab server for the specified user.

        Restriction: A user can only have one lab, please check it before
        calling this function.

        Input:
            user - Username associated with the lab
        Return:
            - (True, json-block), or
            - (False, message) if something goes wrong.
        """
        # Prepare environment
        workspace = os.path.join(JUPYTER_WORKSPACE, username)
        os.makedirs(workspace, exist_ok=True)

        hashed_passwd = passwd(password)
        with open(os.path.join(workspace, '.passwd'), 'w') as f:
            f.write(hashed_passwd)

        # Determine port
        try:
            min_port = int(JUPYTER_LAB_PORTS.split('-')[0])
            max_port = int(JUPYTER_LAB_PORTS.split('-')[1])
        except Exception as err:
            LOG.warning('Fail to get port range for Jupyter labs.', err)
            min_port = max_port = 8888

        labs = self._get_labs()
        if labs:
            port = max([int(x['port']) for x in labs]) + 1
            if port > max_port:
                msg = 'No more labs can be started. (port range: {}~{})'.format(
                    min_port, max_port)
                LOG.error(msg)
                return False, msg
        else:
            port = min_port

        # Start Jupyter lab
        cmd = 'jupyter-lab -y --allow-root --no-browser --collaborative \
            --ip 0.0.0.0 --port {} --notebook-dir={} \
            --ServerApp.password_required=True \
            --ServerApp.password=\'{}\' \
            &>>{}/.jupyter.log &'.format(
            port, workspace, hashed_passwd, workspace
        )
        os.system(cmd)
        
        # Get lab info
        lab = self._get_lab_by_user(username)
        if lab is None:
            msg = 'Fail to create Jupyter lab for user {}.'.format(username)
            LOG.error(msg)
            return False, msg
        return True, lab

    def _stop_lab(self):
        """Stop the JupyterLab server for a specified user.

        Input:
            user - Username associated with the lab
        Return:
            - (True, json-block), or
            - (False, message) if something goes wrong.
        """
        pass

    # Report Functions
    def create_report(self, id):
        """Create the benchmark report in staging area.

        Input:
            id - Benchmark ID
        Return:
            - (True, json-block), or
            - (False, message) if something goes wrong.
        """
        pass

    # Lab Functions
    def query_labs(self):
        """Query information of the running labs.

        Input:
            None
        Return:
            - (True, json-block), or
            - (False, message) if something goes wrong.
        """
        labs = self._get_labs()
        if labs is not None:
            # Remove sensitive information
            for lab in labs:
                lab.pop('line')
                lab.pop('token')
                lab.pop('path')
                lab.pop('hash')

            return True, labs
        else:
            msg = 'Failed to query information of the running labs.'
            LOG.error(msg)
            return False, msg

    def create_lab(self, username, password):
        """Create a Jupyter lab for the specified user.

        Input:
            user - Username associated with the lab
        Return:
            - (True, json-block), or
            - (False, message) if something goes wrong.
        """
        if self._get_lab_by_user(username):
            msg = 'Only one lab can be created for user "{}".'.format(username)
            LOG.error(msg)
            return False, msg

        return self._start_lab(username, password)

    # Study Functions
    def query_studies(self):
        """Query information of the current studies.

        Input:
            user - Owner of the study
        Return:
            - (True, json-block), or
            - (False, message) if something goes wrong.
        """
        studies = self._get_studies()
        if studies is not None:
            return True, studies
        else:
            msg = 'Failed to query information of the current studies.'
            LOG.error(msg)
            return False, msg

    def start_study(self, report_id, username, password):
        """Start a study for a specified user.

        Input:
            user - Owner of the study
        Return:
            - (True, json-block), or
            - (False, message) if something goes wrong.
        """
        # Check if the report exists
        source = os.path.join(PERF_INSIGHT_ROOT, 'reports', report_id)
        if not os.path.isdir(source):
            msg = 'Report ID "{}" does not exist.'.format(id)
            LOG.error(msg)
            return False, msg

        # Check if the report is available for checking out
        studies = self._get_studies()
        if studies is None:
            msg = 'Failed to query information of the current studies.'
            LOG.error(msg)
            return False, msg

        users = [x['user'] for x in studies if x['id'] == report_id]
        if users:
            # Report has been checked out
            msg = 'The report has been checked out by user "{}".'.format(
                ', '.join(users))
            LOG.error(msg)
            return False, msg

        # Check if the user already have a Jupyter lab
        lab = self._get_lab_by_user(username)
        if lab:
            # Verify the password
            if not lab['hash']:
                msg = 'Cannot get hashed password for user "{}".'.format(
                    username)
                LOG.error(msg)
                return False, msg

            if not passwd_check(lab['hash'], password):
                msg = 'Invalid password for user "{}".'.format(username)
                LOG.error(msg)
                return False, msg
        else:
            # TODO: create a lab for the user
            # username, password, port
            lab = self._start_lab()

        # Check out the report
        os.symlink(source, os.path.join(lab['path'], report_id))

        return True, {'id': report_id, 'user': username}

    def stop_study(self):
        """Stop the study for a specified user.

        Input:
            user - Owner of the study
        Return:
            - (True, json-block), or
            - (False, message) if something goes wrong.
        """
        pass


# Flask
app = Flask(__name__)


@app.put('/reports/<id>')
def create_report(id):
    LOG.info('Received request to create report for "{}".'.format(id))
    res, con = helper.create_report(id)
    if res:
        return jsonify(con), 200
    else:
        return jsonify({'error': con}), 500

@app.get('/labs')
def query_labs():
    LOG.info('Received request to query all Jupyter labs.')
    res, con = helper.query_labs()
    if res:
        return jsonify(con), 200
    else:
        return jsonify({'error': con}), 500


@app.post('/labs')
def create_lab():
    LOG.info('Received request to create a Jupyter lab.')

    if request.is_json:
        req = request.get_json()
    else:
        return jsonify({'error': 'Request must be JSON.'}), 415

    # Parse args
    username = req.get('username')
    if username is None:
        return jsonify({'error': '"username" is missing in request.'}), 415

    password = req.get('password')
    if password is None:
        return jsonify({'error': '"password" is missing in request.'}), 415

    # Execute action
    res, con = helper.create_lab(username, password)
    if res:
        return jsonify(con), 200
    else:
        return jsonify({'error': con}), 500


@app.get('/studies')
def query_studies():
    LOG.info('Received request to query all studies.')
    res, con = helper.query_studies()
    if res:
        return jsonify(con), 200
    else:
        return jsonify({'error': con}), 500


@app.put('/studies')
def update_study():
    if request.is_json:
        req = request.get_json()
    else:
        return jsonify({'error': 'Request must be JSON.'}), 415

    # Parse args
    action = req.get('action')
    if action is None:
        return jsonify({'error': '"action" is missing in request.'}), 415
    elif not action in ('start', 'stop'):
        return jsonify({'error': '"action" must be "start" or "stop".'}), 415

    report_id = req.get('report_id')
    if report_id is None:
        return jsonify({'error': '"report_id" is missing in request.'}), 415

    if action == 'start':
        LOG.info('Received request to start a study for "{}".'.format(report_id))
    elif action == 'stop':
        LOG.info('Received request to stop the study for "{}".'.format(report_id))

    username = req.get('username')
    if username is None:
        return jsonify({'error': '"username" is missing in request.'}), 415

    password = req.get('password')
    if password is None:
        return jsonify({'error': '"password" is missing in request.'}), 415

    # Execute action
    if action == 'start':
        res, con = helper.start_study()
    elif action == 'stop':
        res, con = helper.stop_study()

    if res:
        return jsonify(con), 200
    else:
        return jsonify({'error': con}), 500


@app.delete('/studies/<id>')
def stop_study(id):
    LOG.info('Received request to stop a study.')
    res, con = helper.stop_study(id)
    if res:
        return jsonify(con), 200    # use 200 since 204 returns no json
    else:
        return jsonify({'error': con}), 500


# Main
LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')


# Load perf-insight configure
with open(os.path.expanduser('~/.perf-insight.yaml'), 'r') as f:
    user_config = yaml.safe_load(f)

config = user_config.get('global', {})
config.update(user_config.get('jupyter', {}))

PERF_INSIGHT_ROOT = config.get('perf_insight_root', '/mnt/perf-insight')
PERF_INSIGHT_REPO = config.get('perf_insight_repo', '/opt/perf-insight')
PERF_INSIGHT_STAG = os.path.join(PERF_INSIGHT_ROOT, '.staging')
JUPYTER_WORKSPACE = config.get('jupyter_workspace', '/app/workspace')
JUPYTER_LAB_PORTS = config.get('jupyter_lab_ports', '8880-8899')

helper = JupyterHelper()
