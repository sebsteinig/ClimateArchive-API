import xarray as xr

data_dir = "/Volumes/WD_Elements/data/ClimateArchive/"

def extract_annual_data_UM(model_ids, locations, variable):
    results = []
    for model_id, (lat, lon) in zip(model_ids, locations):
        # Load the NetCDF file for the model (this is just an example path)
        ds = xr.open_dataset(f'{data_dir}/{model_id}/climate/{model_id}a.pdclann.nc', decode_times=False)
        # Extract data for the specified location
        data = ds[variable].sel(latitude=lat, longitude=lon, method='nearest').squeeze().values.tolist()

        if variable == 'temp_mm_1_5m':
            # Convert from Kelvin to Celsius
            data = round(data - 273.15, 2) 
            
        results.append(data)
    return results
