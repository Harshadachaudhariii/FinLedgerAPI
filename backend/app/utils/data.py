import json

def load_data():
    with open("./data/transactions.json", "r") as f:
        data = json.load(f)
        return data
    
def save_data(data):
    with open('./data/transactions.json','w') as f:
        json.dump(data, f, indent=4)