import xarray as xr
import logging
import os
import time
from functools import lru_cache

# the actual model data (netcdf files) live outside the Docker container
# when starting the container, we map the directory containing the model data
# as a volume to '/data' inside the container
data_dir = '/data'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('climate_api')

# Define cache for netCDF files
# This dramatically reduces file I/O for frequently accessed files
CACHE_SIZE = int(os.environ.get('NETCDF_CACHE_SIZE', 50))  # Number of files to cache
CACHE_TTL = int(os.environ.get('NETCDF_CACHE_TTL', 3600))  # Time in seconds to keep files in cache (1 hour default)

# Cache for opened netCDF datasets
file_cache = {}
cache_timestamps = {}

def get_cached_dataset(file_path):
    """Get dataset from cache or open and cache it"""
    current_time = time.time()
    
    # Clear expired entries from cache
    expired_files = [f for f, t in cache_timestamps.items() if current_time - t > CACHE_TTL]
    for f in expired_files:
        if f in file_cache:
            file_cache[f].close()  # Properly close xarray datasets
            del file_cache[f]
        if f in cache_timestamps:
            del cache_timestamps[f]
            
    # If cache is too large, remove oldest entries
    if len(file_cache) >= CACHE_SIZE and file_path not in file_cache:
        oldest_file = min(cache_timestamps, key=cache_timestamps.get, default=None)
        if oldest_file:
            file_cache[oldest_file].close()
            del file_cache[oldest_file]
            del cache_timestamps[oldest_file]
    
    # Return cached dataset or open new one
    if file_path in file_cache:
        logger.info(f"Cache hit for {file_path}")
        cache_timestamps[file_path] = current_time  # Update timestamp
        return file_cache[file_path]
    else:
        logger.info(f"Cache miss for {file_path}, loading from disk")
        try:
            dataset = xr.open_dataset(file_path, decode_times=False)
            file_cache[file_path] = dataset
            cache_timestamps[file_path] = current_time
            return dataset
        except Exception as e:
            logger.error(f"Error loading dataset {file_path}: {str(e)}")
            raise

# define the mapping of user input variable names to dataset variable names
variable_name_mapping_UM = {
    'tas': 'temp_mm_1_5m',
    'pr': 'precip_mm_srf'
}

def extract_annual_data_UM(model_ids, locations, user_variable):
    results = []
    # translate user variable name to UM variable name
    variable = variable_name_mapping_UM.get(user_variable)
    
    start_time = time.time()
    for model_id, (lat, lon) in zip(model_ids, locations):
        try:
            file_path = f'{data_dir}/bridge_hadcm3/{model_id}/climate/{model_id}a.pdclann.nc'
            # Use cached dataset instead of opening fresh each time
            ds = get_cached_dataset(file_path)
            
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
            logger.error(f"File not found: {file_path}")
            raise ValueError(f"File not found for model_id: {model_id}")
        except KeyError:
            logger.error(f"Variable '{variable}' not found in dataset for model_id: {model_id}")
            raise ValueError(f"Variable '{variable}' not found in dataset for model_id: {model_id}")
        except Exception as e:
            logger.error(f"Error processing data for model_id {model_id}: {str(e)}")
            raise RuntimeError(f"Error processing data for model_id {model_id}: {str(e)}")
    
    logger.info(f"Processed {len(model_ids)} models in {time.time() - start_time:.2f} seconds")
    return results

def extract_ts_data_cmip(model_id, location, user_variable, frequency):
    # standard CMIP6 variable names
    variable = user_variable
    if model_id == 'PI':
        time_period = 'mean.1850-1900'
    else:
        time_period = 'runmean.2000-2100'

    start_time = time.time()
    try:
        # Determine file path based on frequency
        if (frequency == 'mm'):
            file_path = f'{data_dir}/cmip6/{variable}_mon_mod_{model_id}_192_ave.{time_period}.mm.nc'
        elif (frequency == 'ym'):
            file_path = f'{data_dir}/cmip6/{variable}_mon_mod_{model_id}_192_ave.{time_period}.ym.nc'
        
        # Use cached dataset
        ds = get_cached_dataset(file_path)

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
        logger.error(f"File not found: {file_path}")
        raise ValueError(f"File not found for model_id: {model_id}")
    except KeyError:
        logger.error(f"Variable '{variable}' not found in dataset for model_id: {model_id}")
        raise ValueError(f"Variable '{variable}' not found in dataset for model_id: {model_id}")
    except Exception as e:
        logger.error(f"Error processing data for model_id {model_id}: {str(e)}")
        raise RuntimeError(f"Error processing data for model_id {model_id}: {str(e)}")
    
    logger.info(f"Processed CMIP model {model_id} in {time.time() - start_time:.2f} seconds")
    return data
