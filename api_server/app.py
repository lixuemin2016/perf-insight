import logging
import os
import yaml
import json
from flask import Flask, request, jsonify


class TestRunManager():
    def query_testruns(self):
        """Query all the TestRunIDs from PERF_INSIGHT_ROOT.

        Input:
            None
        Return:
            A list of TestRunIDs.
        """

        testruns = []
        valid_prefix = ('fio_', 'uperf_')
        search_path = os.path.join(PERF_INSIGHT_ROOT, 'testruns')

        if not os.path.isdir(search_path):
            return testruns

        for entry in os.listdir(search_path):
            if not os.path.isdir(os.path.join(search_path, entry)):
                continue
            if entry.startswith(valid_prefix):
                LOG.debug('Found TestRunID "{}".'.format(entry))
                testruns.append({'id': entry})

        return testruns

    def inspect_testrun(self, id):
        """Inspect a specified TestRunID from PERF_INSIGHT_ROOT.

        Input:
            id = TestRunID
        Return:
            A dict of TestRun information.
        """

        search_path = os.path.join(PERF_INSIGHT_ROOT, 'testruns', id)
        if not os.path.isdir(search_path):
            return None

        # Get TestRunID
        testrun = {'id': id}

        # # Get datastore
        # try:
        #     datastore_file = os.path.join(search_path, 'datastore.json')
        #     with open(datastore_file, 'r') as f:
        #         datastore = json.load(f)
        # except Exception as err:
        #     LOG.info('Fail to get datastore from {}. error={}'.format(
        #         datastore_file, err))
        #     datastore = None
        # testrun.update({'datastore': datastore})

        # Get metadata
        try:
            metadata_file = os.path.join(search_path, 'metadata.json')
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        except Exception as err:
            LOG.info('Fail to get metadata from {}. error={}'.format(
                metadata_file, err))
            metadata = None
        testrun.update({'metadata': metadata})

        return testrun

    def load_testrun(self, request):
        """Load TestRun from staged eara.

        Input:
            id = TestRunID (the folder name in staged eara)
        Return:
            A dict of TestRun information.
        """

        # Parse args
        id = request.get('id')
        if id is None:
            LOG.error('"id" is missing in request.')
            return None

        create_datastore = request.get('create_datastore')
        if create_datastore is None:
            LOG.error('"create_datastore" is missing in request.')
            return None
        elif not isinstance(create_datastore, bool):
            LOG.error('"create_datastore" in request must be a bool value.')
            return None

        update_dashboard = request.get('update_dashboard')
        if update_dashboard is None:
            LOG.error('"update_dashboard" is missing in request.')
            return None
        elif not isinstance(update_dashboard, bool):
            LOG.error('"update_dashboard" in request must be a bool value.')
            return None

        generate_plots = request.get('generate_plots')
        if generate_plots is None:
            LOG.error('"generate_plots" is missing in request.')
            return None
        elif not isinstance(generate_plots, bool):
            LOG.error('"generate_plots" in request must be a bool value.')
            return None

        # Criteria check
        search_path = os.path.join(PERF_INSIGHT_ROOT, '.staged', id)
        if not os.path.isdir(search_path):
            LOG.error('Folder "{}" can not be found in staged eara.'.format(id))
            return None

        # Get TestRunID and metadata
        testrun = {'id': id}

        try:
            metadata_file = os.path.join(search_path, 'metadata.json')
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        except Exception as err:
            LOG.info('Fail to get metadata from {}. error={}'.format(
                metadata_file, err))
            metadata = None

        if metadata is None:
            LOG.error('Failed to parse "metadata.json".')
            return None
        else:
            testrun.update({'metadata': metadata})

        if generate_plots:
            pass
        if create_datastore:
            pass
        if update_dashboard:
            pass

    def import_testrun(self):
        pass


LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

app = Flask(__name__)

# Load perf-insight configure
with open(os.path.expanduser('~/.perf-insight.yaml'), 'r') as f:
    user_config = yaml.safe_load(f)

PERF_INSIGHT_ROOT = user_config.get(
    'global', {}).get('perf_insight_root') or '/nfs/perf-insight'
PERF_INSIGHT_REPO = user_config.get(
    'global', {}).get('perf_insight_repo') or '/opt/perf-insight'


testrun_manager = TestRunManager()


@app.route('/testruns')
def query_testruns():
    result = testrun_manager.query_testruns()
    return jsonify({'testruns': {'testrun': result}}), 200


@app.route('/testruns/<id>')
def inspect_testrun(id):
    result = testrun_manager.inspect_testrun(id)
    if result is None:
        return jsonify({'error': 'The requested resource was not found.'}), 404
    else:
        return jsonify({'testrun': result}), 200


@app.route('/testruns', methods=['POST'])
def add_testrun():
    if not request.is_json:
        return {"error": "Request must be JSON"}, 415

    req = request.get_json()
    print(req)

    if req.get('action') == 'load':
        testrun_manager.load_testrun()
    elif req.get('action') == 'import':
        testrun_manager.import_testrun()
    else:
        return {"error": "No action in request or unsupported action."}, 415

    return jsonify(req), 201
