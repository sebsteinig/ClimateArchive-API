from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging
import time
import psutil
import json

app = Flask(__name__)
# Enable CORS for all routes
CORS(app)

from get_model_data import extract_annual_data_UM, extract_ts_data_cmip, logger

# Memory monitoring
def check_memory_usage():
    # Get memory usage details
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    memory_used_mb = memory.used / (1024 * 1024)  # Convert to MB
    memory_total_mb = memory.total / (1024 * 1024)  # Convert to MB
    memory_available_mb = memory.available / (1024 * 1024)  # Convert to MB
    
    return {
        'percent': memory_percent,
        'used_mb': round(memory_used_mb, 2),
        'total_mb': round(memory_total_mb, 2),
        'available_mb': round(memory_available_mb, 2)
    }

# Helper function to safely dump request data for logging
def get_request_data_for_logging(req):
    log_data = {
        'path': req.path,
        'method': req.method,
        'headers': dict(req.headers),
        'remote_addr': req.remote_addr,
    }
    
    # Try to include JSON body if present
    if req.is_json and req.get_data():
        try:
            log_data['json_body'] = req.json
        except:
            log_data['json_body'] = 'Error parsing JSON'
    
    # Remove sensitive headers if any
    if 'Authorization' in log_data['headers']:
        log_data['headers']['Authorization'] = 'REDACTED'
    
    return log_data

# Configure request logging
@app.before_request
def before_request():
    request.start_time = time.time()
    
    # Check memory usage before processing request
    memory_info = check_memory_usage()
    
    # Log detailed request information
    request_data = get_request_data_for_logging(request)
    logger.info(f"Request received: {json.dumps(request_data, default=str)}")
    logger.info(f"Memory usage before request: {memory_info['percent']}% (Used: {memory_info['used_mb']} MB, Available: {memory_info['available_mb']} MB of {memory_info['total_mb']} MB total)")
    
    # If memory usage is critical, return a 503 Service Unavailable
    if memory_info['percent'] > 95:  # 95% threshold
        logger.error(f"Critical memory usage: {memory_info['percent']}% (Used: {memory_info['used_mb']} MB, Available: {memory_info['available_mb']} MB) - Rejecting request")
        return jsonify({
            'error': 'Server is under heavy load, please try again later',
            'status': 'overloaded'
        }), 503

@app.after_request
def after_request(response):
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        memory_info = check_memory_usage()
        logger.info(f"Request to {request.path} completed in {duration:.2f}s - Status: {response.status_code}")
        logger.info(f"Memory usage after request: {memory_info['percent']}% (Used: {memory_info['used_mb']} MB, Available: {memory_info['available_mb']} MB)")
    return response

# Health check endpoint with memory stats
@app.route('/health', methods=['GET'])
def health_check():
    memory_info = check_memory_usage()
    status = 'healthy' if memory_info['percent'] < 80 else 'degraded'
    
    return jsonify({
        'status': status,
        'memory': {
            'percent': memory_info['percent'],
            'used_mb': memory_info['used_mb'],
            'total_mb': memory_info['total_mb'],
            'available_mb': memory_info['available_mb']
        },
        'timestamp': time.time(),
        'api_version': '1.0.0'
    })

#########################################################################################
# BRIDGE annual mean climatology
#########################################################################################

@app.route('/get_mean_data_bridge', methods=['POST', 'OPTIONS'])
def get_mean_data_bridge():
    if request.method == 'OPTIONS':
        return jsonify({})
    
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
        logger.warning(f"Bad request: {str(ve)}")
        return jsonify({'error': str(ve)}), 400  # Bad request
    except RuntimeError as re:
        logger.error(f"Server error: {str(re)}")
        return jsonify({'error': str(re)}), 500  # Internal server error

#########################################################################################
# CMIP6 monthly or annual mean scenario timeseries
#########################################################################################
    
@app.route('/get_ts_data_cmip', methods=['POST', 'OPTIONS'])
def get_ts_data_cmip():
    if request.method == 'OPTIONS':
        return jsonify({})
    
    data = request.json

    # check that the request contains the expected keys
    if not all(key in data for key in ['model_id', 'location', 'variable', 'frequency']):
        return jsonify({'error': 'Missing data. Expected keys are: model_id, location, variable and frequency/'}), 400

    model_id = data['model_id']
    location = data['location']
    variable = data['variable']
    frequency = data['frequency']

    # check for correct API call
    # validate model_ids, locations and variable
    if not isinstance(model_id, str):
        return jsonify({'error': 'model_id should be a single string'}), 400
    if not isinstance(location, list) or not len(location) == 2:
        return jsonify({'error': 'location should be a list of length 2'}), 400
    if not isinstance(variable, str):
        return jsonify({'error': 'variable should be a string'}), 400
    if not isinstance(frequency, str):
        return jsonify({'error': 'frequency should be a string'}), 400

    # validate that known model ID was requested
    if model_id not in ['ssp126', 'ssp245', 'ssp370', 'ssp585', 'PI']:
        return jsonify({'error': f'Unknown model_id: {model_id}. Currently supported model_ids are: ssp126, ssp245, ssp370 and ssp585'}), 400    
    # validate that known variable was requested
    if variable not in ['tas', 'pr']:
        return jsonify({'error': f'Unknown variable: {variable}. Currently supported variables are: tas and pr'}), 400
    # validate that known time frequency was requested
    if frequency not in ['mm', 'ym']:
        return jsonify({'error': f'Unknown time frequency: {frequency}. Currently supported samplings are: mm and ym'}), 400

    # try to extract the data
    try:
        results = extract_ts_data_cmip(model_id, location, variable, frequency)
        return jsonify(results)
    except ValueError as ve:
        logger.warning(f"Bad request: {str(ve)}")
        return jsonify({'error': str(ve)}), 400  # Bad request
    except RuntimeError as re:
        logger.error(f"Server error: {str(re)}")
        return jsonify({'error': str(re)}), 500  # Internal server error

if __name__ == '__main__':
    host = os.environ.get('API_HOST', '0.0.0.0')
    port = int(os.environ.get('API_PORT', 4000))
    debug = os.environ.get('API_DEBUG', 'False').lower() == 'true'
    
    # Log system resources at startup
    memory_info = check_memory_usage()
    logger.info(f"Starting ClimateArchive API on {host}:{port} (debug={debug})")
    logger.info(f"Initial memory usage: {memory_info['percent']}% (Used: {memory_info['used_mb']} MB, Available: {memory_info['available_mb']} MB of {memory_info['total_mb']} MB total)")
    
    app.run(host=host, port=port, debug=debug)
