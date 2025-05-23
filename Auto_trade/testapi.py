import requests

def test_mexc_contract_ping():
    url = "https://contract.mexc.com/api/v1/contract/ping"
    try:
        response = requests.get(url, timeout=10)
        print("Status code:", response.status_code)
        print("Response:", response.text)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_mexc_contract_ping()