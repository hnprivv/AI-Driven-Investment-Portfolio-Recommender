import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import joblib

# 1. Load Data
try:
    df = pd.read_csv('./data/user_profile.csv')
    print("✅ Data loaded successfully.")
except FileNotFoundError:
    print("❌ Error: user_profile.csv not found.")
    exit()

# 2. Preprocessing / Encoding
income_map = {
    '< 25,000': 1, 
    '25,000 - 50,000': 2, 
    '50,000 - 100,000': 3, 
    '100,000+': 4
}

horizon_map = {
    '1 Year': 1, 
    '3-5 Years': 3, 
    '5-10 Years': 5, 
    '10+ Years': 10
}

experience_map = {
    'Beginner': 1, 
    'Intermediate': 2, 
    'Advanced': 3
}

# Apply mappings
X = pd.DataFrame()
X['Age'] = df['Age']
X['Income_Score'] = df['Income Range'].map(income_map).fillna(1) # Default to 1 if unknown
X['Risk_Score'] = df['Risk Tolerance'] # Already numeric (1-10)
X['Horizon_Score'] = df['Investment Horizon'].map(horizon_map).fillna(1)
X['Exp_Score'] = df['Experience'].map(experience_map).fillna(1)

# 3. Scaling
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 4. Train K-Means
kmeans = KMeans(n_clusters=4, random_state=42)
kmeans.fit(X_scaled)

# 5. Save the model
joblib.dump(kmeans, './modules/model/kmeans_model.pkl')
joblib.dump(scaler, './modules/model/scaler.pkl')

print("✅ Model trained and saved as 'kmeans_model.pkl'")
print("✅ Scaler saved as 'scaler.pkl'")
print("🚀 You can now use Live Clustering in your app!")