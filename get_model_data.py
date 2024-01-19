import xarray as xr
import logging

# the actual model data (netcdf files) live outside the Docker container
# when starting the container, we map the directory containing the model data
# as a volume to '/data' inside the container
data_dir = '/data'

# define the mapping of user input variable names to dataset variable names
variable_name_mapping_UM = {
    'tas': 'temp_mm_1_5m',
    'pr': 'precip_mm_srf'
}

def extract_annual_data_UM(model_ids, locations, user_variable):
    results = []
    # translate user variable name to UM variable name
    variable = variable_name_mapping_UM.get(user_variable)
    for model_id, (lat, lon) in zip(model_ids, locations):
        try:
            # Load the NetCDF file for the model (this is just an example path)
            ds = xr.open_dataset(f'{data_dir}/bridge_hadcm3/{model_id}/climate/{model_id}a.pdclann.nc', decode_times=False)
            # convert longitude from -180 to 180 to 0 to 360
            lon = (lon + 360) % 360
            # Extract data for the specified location
            data = ds[variable].sel(latitude=lat, longitude=lon, method='nearest').squeeze().values.tolist()

            if variable == 'temp_mm_1_5m':
                # Convert from Kelvin to Celsius
                data = round(data - 273.15, 2) 
            elif variable == 'precip_mm_srf':
                # Convert from kg/m^2/s to mm/day
                data = round(data * 86400, 2)
                
            results.append(data)

        except FileNotFoundError:
            raise ValueError(f"File not found for model_id: {model_id}")
        except KeyError:
            raise ValueError(f"Variable '{variable}' not found in dataset for model_id: {model_id}")
        except Exception as e:
            raise RuntimeError(f"Error processing data for model_id {model_id}: {str(e)}")
        
    return results

def extract_ts_data_cmip(model_id, location, user_variable):
    # standard CMIP6 variable names
    variable = user_variable
    try:
        # Load the NetCDF file for the model (this is just an example path)
        ds = xr.open_dataset(f'{data_dir}/cmip6/{variable}_mon_mod_{model_id}_192_ave.ym.nc', decode_times=False)

        lat = location[0]
        lon = location[1]
        # convert longitude from -180 to 180 to 0 to 360
        lon = (lon + 360) % 360

        # Extract data for the specified location
        data = ds[variable].sel(lat=lat, lon=lon, method='nearest').squeeze().values.tolist()

        if variable == 'tas':
            # Convert from Kelvin to Celsius for each element in the list
            data = [round(datum - 273.15, 2) for datum in data]
        elif variable == 'pr':
            # Convert from kg/m^2/s to mm/day for each element in the list
            data = [round(datum * 86400, 2) for datum in data]
    
    except FileNotFoundError:
        raise ValueError(f"File not found for model_id: {model_id}")
    except KeyError:
        raise ValueError(f"Variable '{variable}' not found in dataset for model_id: {model_id}")
    except Exception as e:
        raise RuntimeError(f"Error processing data for model_id {model_id}: {str(e)}")
        
    return data
