from flask import Flask, request, jsonify
app = Flask(__name__)

from get_model_data import extract_annual_data_UM, extract_ts_data_cmip

#########################################################################################
# BRIDGE annual mean climatology
#########################################################################################

@app.route('/get_mean_data_bridge', methods=['POST'])
def get_mean_data_bridge():
    data = request.json

    # check that the request contains the expected keys
    if not all(key in data for key in ['model_ids', 'locations', 'variable']):
        return jsonify({'error': 'Missing data. Expected keys are: model_ids, locations and variable'}), 400

    model_ids = data['model_ids']
    locations = data['locations']
    variable = data['variable']

    # check for correct API call
    # validate model_ids and locations
    if not isinstance(model_ids, list) or not all(isinstance(id, str) for id in model_ids):
        return jsonify({'error': 'model_ids should be a list of strings'}), 400
    if not isinstance(locations, list) or not all(isinstance(loc, (list, tuple)) and len(loc) == 2 for loc in locations):
        return jsonify({'error': 'locations should be a list of tuples'}), 400

    # check if the length of model_ids and locations is the same
    if len(model_ids) != len(locations):
        return jsonify({'error': 'model_ids and locations must have the same length'}), 400

    # validate variable: should be a string
    if not isinstance(variable, str):
        return jsonify({'error': 'variable should be a string'}), 400
    
    # validate that known variable was requested
    if variable not in ['tas', 'pr']:
        return jsonify({'error': f'Unknown variable: {variable}. Currently supported variables are: tas and pr'}), 400

    # try to extract the data
    try:
        results = extract_annual_data_UM(model_ids, locations, variable)
        return jsonify(results)
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400  # Bad request
    except RuntimeError as re:
        return jsonify({'error': str(re)}), 500  # Internal server error

#########################################################################################
# CMIP6 annual mean scneario timeseries
#########################################################################################
    
@app.route('/get_ts_data_cmip', methods=['POST'])
def get_ts_data_cmip():
    data = request.json

    # check that the request contains the expected keys
    if not all(key in data for key in ['model_id', 'location', 'variable']):
        return jsonify({'error': 'Missing data. Expected keys are: model_id, location and variable'}), 400

    model_id = data['model_id']
    location = data['location']
    variable = data['variable']

    # check for correct API call
    # validate model_ids, locations and variable
    if not isinstance(model_id, str):
        return jsonify({'error': 'model_id should be a single string'}), 400
    if not model_id in ['ssp126', 'ssp245', 'ssp370', 'ssp585']:
        return jsonify({'error': f'Unknown model_id: {model_id}. Currently supported model_ids are: ssp126, ssp245, ssp370 and ssp585'}), 400
    if not isinstance(location, list) or not len(location) == 2:
        return jsonify({'error': 'location should be a list of length 2'}), 400
    if not isinstance(variable, str):
        return jsonify({'error': 'variable should be a string'}), 400
    
    # validate that known variable was requested
    if variable not in ['tas', 'pr']:
        return jsonify({'error': f'Unknown variable: {variable}. Currently supported variables are: tas and pr'}), 400

    # try to extract the data
    try:
        results = extract_ts_data_cmip(model_id, location, variable)
        return jsonify(results)
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400  # Bad request
    except RuntimeError as re:
        return jsonify({'error': str(re)}), 500  # Internal server error

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=False)
