# Weight and Balance
This is a simple weight and balance PDF generator for aircraft. Currently, it only supports the Cessna 172S model and the Breezer C (without graph).

## Usage
Enter the name and weights of persons/baggage in `weight_and_balance.json`. 
This will then be loaded into the python script when running `python weight_and_balance.py`
A pdf is automatically generated in this folder after the script finishes.

##### Note
I have tested the graph lines for CoG and weight, but it still may fail. Double check they make sense before trusting them.