from flask import Flask, request, jsonify
app = Flask(__name__)

from get_model_data import extract_annual_data_UM

@app.route('/get_model_data', methods=['POST'])
def get_model_data():
    data = request.json
    model_ids = data['model_ids']
    locations = data['locations']
    variable = data['variable']

    results = extract_annual_data_UM(model_ids, locations, variable)
    # Convert results to a serializable format if necessary
    return jsonify(results)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=True)
