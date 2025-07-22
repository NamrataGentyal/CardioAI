from flask import Flask, render_template, request,jsonify
import numpy as np
import pickle

app = Flask(__name__)
model = pickle.load(open("model.pkl", "rb"))
scaler = pickle.load(open("scaler.pkl", "rb"))

@app.route("/")
def home():
    return render_template('index.html')

@app.route("/predict", methods=["POST"])
def predict():
    float_feature = [float(x) for x in request.form.values()]
    features = [np.array(float_feature)]
    input_scaled = scaler.transform(features)
    prediction = model.predict(input_scaled)[0]
    result = "Heart Failure Detected" if prediction == 1 else "No Heart Failure"
    return render_template('index.html', result=result)

if __name__ == '__main__':
    app.run(debug=True, port=3000)
