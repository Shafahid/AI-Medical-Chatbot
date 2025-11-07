# 🤖 Autoencoder Anomaly Detection Workflow

Complete documentation of the ML-based fraud detection system in the TrustWallet application.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Frontend Flow](#frontend-flow)
4. [Backend Flow](#backend-flow)
5. [ML Model Processing](#ml-model-processing)
6. [Risk Level Mapping](#risk-level-mapping)
7. [Complete Request-Response Cycle](#complete-request-response-cycle)
8. [Model Artifacts](#model-artifacts)
9. [Feature Engineering](#feature-engineering)
10. [Example Scenarios](#example-scenarios)

---

## 🎯 Overview

The system uses an **Autoencoder Neural Network** to detect fraudulent transactions by learning patterns from normal transactions. Any transaction that deviates significantly from learned patterns is flagged as anomalous.

### Key Concepts

- **Autoencoder**: A neural network that learns to compress and reconstruct normal transaction patterns
- **Reconstruction Error**: Measures how well the model can reconstruct a transaction (higher = more unusual)
- **Threshold**: The boundary between normal and anomalous behavior (default: 1.96)
- **Double-Check**: ML runs twice (preview + confirm) for enhanced security

### Risk Levels

| Risk Level | Reconstruction Error | Action                         |
| ---------- | -------------------- | ------------------------------ |
| **Low**    | < 1.47               | ✅ Proceed automatically       |
| **Medium** | 1.47 - 2.94          | ⚠️ Show warning, allow proceed |
| **High**   | ≥ 2.94               | 🚫 Block transaction           |

---

## 🏗️ Architecture

```
┌─────────────┐
│   Flutter   │
│  Frontend   │
└──────┬──────┘
       │
       │ 1. POST /wallet/preview-send
       │    { receiver_phone, amount }
       ↓
┌─────────────┐
│   FastAPI   │
│   Backend   │
└──────┬──────┘
       │
       │ 2. Build features
       ↓
┌─────────────────┐
│  Autoencoder    │
│     Model       │
│ (TensorFlow)    │
└──────┬──────────┘
       │
       │ 3. Returns reconstruction_error
       ↓
┌─────────────┐
│ Risk Level  │
│  Mapping    │
└──────┬──────┘
       │
       │ 4. Response with risk_level
       ↓
┌─────────────┐
│   Flutter   │
│  (Display)  │
└─────────────┘
```

---

## 📱 Frontend Flow

### Step 1: User Input (send_entry_screen.dart)

```dart
// User fills the form
Phone: 01712345678
Amount: 500.00
```

### Step 2: Call Preview API

```dart
// send_entry_screen.dart - Line ~200
final response = await http.post(
  Uri.parse('http://YOUR_IP:8000/api/v1/wallet/preview-send'),
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer eyJ0eXAiOiJKV1Qi...',
  },
  body: jsonEncode({
    'receiver_phone': '01712345678',
    'amount': 500.00,
  }),
);
```

**Request Payload:**

```json
{
  "receiver_phone": "01712345678",
  "amount": 500.0
}
```

### Step 3: Handle Response

```dart
// Line ~210
final responseData = jsonDecode(response.body);

if (response.statusCode == 200) {
  final riskLevel = responseData['risk_check']['risk_level'];

  if (riskLevel == 'high') {
    _showHighRiskDialog(context, responseData);
  } else if (riskLevel == 'medium') {
    _showMediumRiskDialog(context, responseData);
  } else {
    _navigateToConfirm(responseData);
  }
}
```

**Response Payload:**

```json
{
  "sender_balance": 10000.0,
  "receiver_name": "John Doe",
  "amount": 500.0,
  "fee": 0.0,
  "risk_check": {
    "risk_level": "low",
    "risk_score": 0.234,
    "threshold": 1.96,
    "can_proceed": true,
    "warnings": []
  },
  "can_proceed": true
}
```

### Step 4: Navigate to Confirm Screen

```dart
// Line ~350
context.push('/send/confirm', extra: {
  'receiver_name': 'John Doe',
  'receiver_phone': '01712345678',
  'amount': 500.00,
  'fee': 0.0,
  'risk_level': 'low',
  'risk_score': 0.234,
});
```

### Step 5: User Confirms Transaction

```dart
// send_confirm_screen.dart - Line ~150
final response = await http.post(
  Uri.parse('http://YOUR_IP:8000/api/v1/wallet/confirm-send'),
  headers: authHeaders(),
  body: jsonEncode({
    'receiver_phone': '01712345678',
    'amount': 500.00,
  }),
);
```

### Step 6: Display Result

```dart
// Line ~170
if (response.statusCode == 200) {
  final data = jsonDecode(response.body);
  _showSuccessDialog(context, data['transaction_id']);
} else {
  _showErrorDialog(context, errorMessage);
}
```

---

## 🖥️ Backend Flow

### Step 1: Receive Preview Request

```python
# transaction_routes.py - Line 397
@router.post("/wallet/preview-send", response_model=PreviewSendResponse)
async def preview_send_money(
    request: SendMoneyRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
```

**Input:**

```python
request.receiver_phone = "01712345678"
request.amount = 500.00
current_user.id = "96cc7d3f-e0e6-407c-9b09-09313d8f15e8"
```

### Step 2: Validate Receiver

```python
# Line 408
receiver = session.exec(
    select(User).where(User.phone_number == request.receiver_phone)
).first()

if not receiver:
    raise HTTPException(status_code=404, detail="Receiver not found")
```

### Step 3: Check Sender Balance

```python
# Line 415
sender_wallet = session.exec(
    select(Wallet).where(Wallet.user_id == current_user.id)
).first()

if sender_wallet.balance < request.amount:
    raise HTTPException(status_code=400, detail="Insufficient balance")
```

### Step 4: Query Transaction History

```python
# Line 425 - Get sender's transaction stats
sender_transactions = session.exec(
    select(Transaction).where(
        or_(
            Transaction.sender_id == current_user.id,
            Transaction.receiver_id == current_user.id
        )
    )
).all()

sender_tx_count = len(sender_transactions)
sender_avg_amount = sum(tx.amount for tx in sender_transactions) / sender_tx_count if sender_tx_count > 0 else 0.0
sender_frequency = sender_tx_count / 30.0  # transactions per day (last 30 days)

# Line 435 - Get receiver's transaction stats
receiver_transactions = session.exec(
    select(Transaction).where(
        or_(
            Transaction.sender_id == receiver.id,
            Transaction.receiver_id == receiver.id
        )
    )
).all()

receiver_tx_count = len(receiver_transactions)
receiver_avg_amount = sum(tx.amount for tx in receiver_transactions) / receiver_tx_count if receiver_tx_count > 0 else 0.0
receiver_frequency = receiver_tx_count / 30.0
```

### Step 5: Build ML Features

```python
# Line 445
from datetime import datetime
now = datetime.now()

transaction_features = {
    # Categorical features
    "product_category": "money_transfer",
    "product_name": "wallet_send",
    "merchant_name": "trustwallet",
    "payment_method": "wallet",
    "transaction_status": "pending",
    "device_type": "mobile",
    "location": "dhaka",

    # Transaction details
    "product_amount": float(request.amount),          # 500.00
    "transaction_fee": 0.0,
    "cashback": 0.0,
    "loyalty_points": 0.0,

    # Sender behavior
    "user_tx_count": sender_tx_count,                 # 5
    "user_avg_amount": sender_avg_amount,             # 450.00
    "user_freq": sender_frequency,                    # 0.167 tx/day

    # Receiver behavior
    "merch_tx_count": receiver_tx_count,              # 3
    "merch_avg_amount": receiver_avg_amount,          # 300.00
    "merchant_freq": receiver_frequency,              # 0.1 tx/day

    # Temporal features
    "hour": now.hour,                                 # 14 (2 PM)
    "day": now.day,                                   # 7
    "month": now.month,                               # 11 (November)
}
```

### Step 6: Call ML Model

```python
# Line 470
from ..utils.autoencoder_model import predict_raw_autoencoder

ml_result = predict_raw_autoencoder(transaction_features)
```

**ML Result:**

```python
{
    "is_anomaly": 0,                    # 0 = normal, 1 = anomaly
    "reconstruction_error": 0.234,      # How unusual this transaction is
    "threshold": 1.96                   # Anomaly boundary
}
```

### Step 7: Map to Risk Level

```python
# Line 475
def map_risk_level(reconstruction_error: float, threshold: float) -> str:
    if reconstruction_error >= threshold * 1.5:      # ≥ 2.94
        return "high"
    elif reconstruction_error >= threshold * 0.75:   # ≥ 1.47
        return "medium"
    else:                                            # < 1.47
        return "low"

risk_level = map_risk_level(
    ml_result["reconstruction_error"],  # 0.234
    ml_result["threshold"]              # 1.96
)
# Returns: "low"
```

### Step 8: Generate Warnings (if needed)

```python
# Line 485
warnings = []
if risk_level == "high":
    warnings.append("Transaction flagged as high risk by fraud detection")
    warnings.append("Unusual transaction pattern detected")
elif risk_level == "medium":
    warnings.append("Transaction requires additional verification")
```

### Step 9: Build Response

```python
# Line 495
return PreviewSendResponse(
    sender_balance=sender_wallet.balance,           # 10000.00
    receiver_name=receiver.full_name,               # "John Doe"
    amount=request.amount,                          # 500.00
    fee=0.0,
    risk_check=RiskCheckResult(
        risk_level=risk_level,                      # "low"
        risk_score=ml_result["reconstruction_error"], # 0.234
        threshold=ml_result["threshold"],            # 1.96
        can_proceed=(risk_level != "high"),         # True
        warnings=warnings                            # []
    ),
    can_proceed=(risk_level != "high")              # True
)
```

---

## 🧠 ML Model Processing

### Autoencoder Model File: `src/utils/autoencoder_model.py`

#### Function: `predict_raw_autoencoder(data: Dict[str, Any])`

#### Step 1: Load Model Artifacts

```python
# Line 68-75
model = load_autoencoder()           # autoencoder_anomaly_model.keras
scaler = load_scaler()               # scaler.pkl
label_encoders = load_label_encoders()  # label_encoders.pkl
threshold = get_threshold()          # 1.96 (from env or default)
```

**Model Files Location:**

- Primary: `models/`
- Fallback: `ai_models/`

#### Step 2: Encode Categorical Features

```python
# Line 77-95
categorical_cols = [
    "product_category",    # "money_transfer"
    "product_name",        # "wallet_send"
    "merchant_name",       # "trustwallet"
    "payment_method",      # "wallet"
    "transaction_status",  # "pending"
    "device_type",         # "mobile"
    "location",            # "dhaka"
]

encoded_features = []
for col in categorical_cols:
    le = label_encoders.get(col)
    val = data.get(col)

    if le and val in le.classes_:
        # Known value: encode using LabelEncoder
        encoded = int(le.transform([val])[0])
        # Example: "mobile" → 2, "wallet" → 1
    else:
        # Unknown value: use -1
        encoded = -1

    encoded_features.append(encoded)

# Result: [1, 2, 0, 1, 0, 2, 0]  (7 categorical features)
```

#### Step 3: Process Numerical Features

```python
# Line 97-113
import math

numerical_features = [
    math.log1p(data["product_amount"]),      # log(500) = 6.215
    math.log1p(data["transaction_fee"]),     # log(0) = 0.0
    math.log1p(data["cashback"]),            # log(0) = 0.0
    math.log1p(data["loyalty_points"]),      # log(0) = 0.0
    data["user_tx_count"],                   # 5
    math.log1p(data["user_avg_amount"]),     # log(450) = 6.111
    data["user_freq"],                       # 0.167
    data["merch_tx_count"],                  # 3
    math.log1p(data["merch_avg_amount"]),    # log(300) = 5.704
    data["merchant_freq"],                   # 0.1
    data["hour"],                            # 14
    data["day"],                             # 7
    data["month"],                           # 11
]

# Result: [6.215, 0.0, 0.0, 0.0, 5, 6.111, 0.167, 3, 5.704, 0.1, 14, 7, 11]  (13 features)
```

**Why log1p?**

- Handles large value ranges (amounts can be 10 or 100,000)
- `log1p(x) = log(1 + x)` prevents log(0) errors
- Makes distribution more normal

#### Step 4: Combine Features

```python
# Line 115
full_input = np.array(
    encoded_features + numerical_features,
    dtype=float
).reshape(1, -1)

# Shape: (1, 20)
# [1, 2, 0, 1, 0, 2, 0, 6.215, 0.0, 0.0, 0.0, 5, 6.111, 0.167, 3, 5.704, 0.1, 14, 7, 11]
```

#### Step 5: Scale Features

```python
# Line 118
scaled = scaler.transform(full_input)

# StandardScaler normalizes to mean=0, std=1
# Example before: [1, 2, 0, 6.215, 5, ...]
# Example after:  [0.23, 0.87, -1.2, 0.45, 0.12, ...]
```

#### Step 6: Autoencoder Reconstruction

```python
# Line 119
reconstructed = model.predict(scaled)

# Autoencoder tries to recreate the input
# Input:  [0.23, 0.87, -1.2, 0.45, 0.12, ...]
# Output: [0.25, 0.85, -1.18, 0.47, 0.13, ...]
#         ↑ Slightly different if anomalous
```

**How Autoencoder Works:**

```
Input (20 features) → Encoder → Bottleneck (8 neurons) → Decoder → Output (20 features)

Normal transaction:   Input ≈ Output (low error)
Anomalous transaction: Input ≠ Output (high error)
```

#### Step 7: Calculate Reconstruction Error

```python
# Line 120
recon_error = float(np.mean(np.square(scaled - reconstructed)))

# Mean Squared Error (MSE) between input and output
# Example:
# Normal:  MSE = 0.234 (< threshold 1.96) ✅
# Anomaly: MSE = 3.456 (> threshold 1.96) 🚫
```

#### Step 8: Classify as Anomaly

```python
# Line 121
is_anomaly = int(recon_error > threshold)

# If reconstruction_error > 1.96:
#     is_anomaly = 1  (flagged)
# Else:
#     is_anomaly = 0  (normal)
```

#### Step 9: Return Result

```python
# Line 123-127
return {
    "is_anomaly": is_anomaly,              # 0 or 1
    "reconstruction_error": recon_error,   # 0.234
    "threshold": threshold,                # 1.96
}
```

---

## 📊 Risk Level Mapping

### Mapping Function (transaction_routes.py)

```python
def map_risk_level(reconstruction_error: float, threshold: float) -> str:
    """Map reconstruction error to human-readable risk level."""

    if reconstruction_error >= threshold * 1.5:      # ≥ 2.94
        return "high"
    elif reconstruction_error >= threshold * 0.75:   # ≥ 1.47
        return "medium"
    else:                                            # < 1.47
        return "low"
```

### Risk Thresholds Table

| Reconstruction Error | Multiplier   | Risk Level | Action          |
| -------------------- | ------------ | ---------- | --------------- |
| 0.00 - 1.46          | < 0.75x      | **Low**    | ✅ Auto-proceed |
| 1.47 - 2.93          | 0.75x - 1.5x | **Medium** | ⚠️ Show warning |
| 2.94+                | ≥ 1.5x       | **High**   | 🚫 Block        |

### Examples

| Error | Calculation         | Level  | Frontend Behavior             |
| ----- | ------------------- | ------ | ----------------------------- |
| 0.234 | 0.234 < 1.47        | Low    | Proceed to confirm screen     |
| 1.789 | 1.47 ≤ 1.789 < 2.94 | Medium | Show warning dialog + proceed |
| 3.456 | 3.456 ≥ 2.94        | High   | Show error dialog + block     |

---

## 🔄 Complete Request-Response Cycle

### Cycle 1: Preview (First ML Check)

```
┌──────────┐
│  Flutter │
└────┬─────┘
     │
     │ POST /wallet/preview-send
     │ {
     │   "receiver_phone": "01712345678",
     │   "amount": 500.00
     │ }
     ↓
┌──────────┐
│  FastAPI │
│          │
│ 1. Validate receiver ✓
│ 2. Check balance ✓
│ 3. Build features → ML
│ 4. Map risk level
│          │
└────┬─────┘
     │
     │ Response:
     │ {
     │   "sender_balance": 10000.00,
     │   "receiver_name": "John Doe",
     │   "amount": 500.00,
     │   "fee": 0.0,
     │   "risk_check": {
     │     "risk_level": "low",
     │     "risk_score": 0.234,
     │     "threshold": 1.96,
     │     "can_proceed": true,
     │     "warnings": []
     │   }
     │ }
     ↓
┌──────────┐
│  Flutter │
│          │
│ if low: navigate
│ if medium: warn + navigate
│ if high: block
│          │
└──────────┘
```

### Cycle 2: Confirm (Second ML Check)

```
┌──────────┐
│  Flutter │
│ (Confirm │
│  Screen) │
└────┬─────┘
     │
     │ POST /wallet/confirm-send
     │ {
     │   "receiver_phone": "01712345678",
     │   "amount": 500.00
     │ }
     ↓
┌──────────┐
│  FastAPI │
│          │
│ 1. Run ML AGAIN
│ 2. Block if high risk
│ 3. Create transaction
│ 4. Update balances
│          │
└────┬─────┘
     │
     │ Response:
     │ {
     │   "transaction_id": "cf18b453-...",
     │   "status": "completed",
     │   "amount": 500.00,
     │   "new_balance": 9500.00,
     │   "ml_warning": null
     │ }
     ↓
┌──────────┐
│  Flutter │
│          │
│ Show success dialog
│ Navigate to home
│          │
└──────────┘
```

---

## 📦 Model Artifacts

### Required Files

```
models/
├── autoencoder_anomaly_model.keras   # TensorFlow Keras model (neural network)
├── scaler.pkl                        # StandardScaler (feature normalization)
└── label_encoders.pkl                # Dict of LabelEncoders (categorical encoding)
```

### File Details

#### 1. `autoencoder_anomaly_model.keras`

- **Type**: TensorFlow/Keras model
- **Architecture**: Autoencoder neural network
- **Input**: 20 features (7 categorical + 13 numerical)
- **Output**: 20 reconstructed features
- **Training**: Trained on normal transactions only
- **Purpose**: Learns normal transaction patterns

**Model Structure:**

```
Input Layer (20)
    ↓
Dense Layer (16, relu)
    ↓
Dense Layer (8, relu)  ← Bottleneck (compressed representation)
    ↓
Dense Layer (16, relu)
    ↓
Output Layer (20)
```

#### 2. `scaler.pkl`

- **Type**: Scikit-learn StandardScaler
- **Purpose**: Normalizes features to mean=0, std=1
- **Applied to**: All 20 features (after encoding)
- **Formula**: `(x - mean) / std`

**Example:**

```python
# Before scaling:
[1, 2, 0, 6.215, 5, 6.111, 0.167, 3, 5.704, 0.1, 14, 7, 11]

# After scaling:
[0.23, 0.87, -1.2, 0.45, 0.12, 0.34, -0.56, -0.23, 0.28, -0.67, 0.91, -0.12, 0.45]
```

#### 3. `label_encoders.pkl`

- **Type**: Dictionary of LabelEncoder objects
- **Keys**: Categorical column names
- **Values**: Fitted LabelEncoder for each column
- **Purpose**: Converts strings to integers

**Structure:**

```python
{
    "product_category": LabelEncoder(classes=['money_transfer', 'bill_payment', ...]),
    "product_name": LabelEncoder(classes=['wallet_send', 'wallet_receive', ...]),
    "merchant_name": LabelEncoder(classes=['trustwallet', 'bkash', 'nagad', ...]),
    "payment_method": LabelEncoder(classes=['wallet', 'card', 'bank', ...]),
    "transaction_status": LabelEncoder(classes=['pending', 'completed', 'failed']),
    "device_type": LabelEncoder(classes=['mobile', 'web', 'tablet']),
    "location": LabelEncoder(classes=['dhaka', 'chittagong', 'sylhet', ...]),
}
```

**Example Encoding:**

```python
# "mobile" → 2
# "wallet" → 1
# "money_transfer" → 0
# "trustwallet" → 0
```

### Loading Mechanism

```python
# autoencoder_model.py - Line 28-39
DEFAULT_MODEL_DIRS = [
    os.path.join(os.getcwd(), "models"),      # Try first
    os.path.join(os.getcwd(), "ai_models"),   # Fallback
]

def _resolve_path(filename: str) -> str:
    for base in DEFAULT_MODEL_DIRS:
        path = os.path.join(base, filename)
        if os.path.exists(path):
            return path
    # Default to first dir if not found
    return os.path.join(DEFAULT_MODEL_DIRS[0], filename)
```

---

## 🛠️ Feature Engineering

### Feature Categories

#### 1. Categorical Features (7)

| Feature              | Type   | Example          | Encoded |
| -------------------- | ------ | ---------------- | ------- |
| `product_category`   | String | "money_transfer" | 0       |
| `product_name`       | String | "wallet_send"    | 2       |
| `merchant_name`      | String | "trustwallet"    | 0       |
| `payment_method`     | String | "wallet"         | 1       |
| `transaction_status` | String | "pending"        | 0       |
| `device_type`        | String | "mobile"         | 2       |
| `location`           | String | "dhaka"          | 0       |

**Encoding Process:**

```python
# Original: "mobile"
# LabelEncoder: {"mobile": 2, "web": 1, "tablet": 0}
# Encoded: 2
```

#### 2. Transaction Features (4)

| Feature           | Type  | Transform | Example          |
| ----------------- | ----- | --------- | ---------------- |
| `product_amount`  | Float | log1p     | log(500) = 6.215 |
| `transaction_fee` | Float | log1p     | log(0) = 0.0     |
| `cashback`        | Float | log1p     | log(0) = 0.0     |
| `loyalty_points`  | Float | log1p     | log(0) = 0.0     |

**Why log1p?**

- Compresses large ranges (10 to 100,000)
- Handles zero values (log(1+0) = 0)
- Makes distribution more normal

#### 3. User Behavior Features (3)

| Feature           | Calculation                                      | Example          |
| ----------------- | ------------------------------------------------ | ---------------- |
| `user_tx_count`   | COUNT(transactions WHERE sender/receiver = user) | 5                |
| `user_avg_amount` | AVG(amount)                                      | log(450) = 6.111 |
| `user_freq`       | tx_count / 30 days                               | 5/30 = 0.167     |

**Purpose:** Detect unusual behavior for this specific user

#### 4. Receiver/Merchant Behavior Features (3)

| Feature            | Calculation                                          | Example          |
| ------------------ | ---------------------------------------------------- | ---------------- |
| `merch_tx_count`   | COUNT(transactions WHERE sender/receiver = receiver) | 3                |
| `merch_avg_amount` | AVG(amount)                                          | log(300) = 5.704 |
| `merchant_freq`    | tx_count / 30 days                                   | 3/30 = 0.1       |

**Purpose:** Detect unusual receiver patterns (e.g., new account receiving large amounts)

#### 5. Temporal Features (3)

| Feature | Type           | Example       |
| ------- | -------------- | ------------- |
| `hour`  | Integer (0-23) | 14 (2 PM)     |
| `day`   | Integer (1-31) | 7             |
| `month` | Integer (1-12) | 11 (November) |

**Purpose:** Detect unusual timing (e.g., large transfers at 3 AM)

### Complete Feature Vector Example

```python
# Transaction: Send 500 BDT to 01712345678 at 2:00 PM

features = [
    # Categorical (encoded)
    0,      # product_category: money_transfer
    2,      # product_name: wallet_send
    0,      # merchant_name: trustwallet
    1,      # payment_method: wallet
    0,      # transaction_status: pending
    2,      # device_type: mobile
    0,      # location: dhaka

    # Transaction
    6.215,  # log(product_amount): log(500)
    0.0,    # log(transaction_fee): log(0)
    0.0,    # log(cashback): log(0)
    0.0,    # log(loyalty_points): log(0)

    # User behavior
    5,      # user_tx_count
    6.111,  # log(user_avg_amount): log(450)
    0.167,  # user_freq: 5 tx / 30 days

    # Receiver behavior
    3,      # merch_tx_count
    5.704,  # log(merch_avg_amount): log(300)
    0.1,    # merchant_freq: 3 tx / 30 days

    # Temporal
    14,     # hour: 2 PM
    7,      # day: 7th
    11,     # month: November
]

# Total: 20 features
```

---

## 💡 Example Scenarios

### Scenario 1: Normal Transaction (Low Risk)

**Input:**

```json
{
  "receiver_phone": "01712345678",
  "amount": 500.0
}
```

**Features:**

- User has 5 previous transactions
- Average amount: 450 BDT
- Receiver has 3 transactions
- Time: 2:00 PM (normal hours)
- Amount: Similar to user's average

**ML Processing:**

```
Reconstruction Error: 0.234
Threshold: 1.96
Ratio: 0.234 / 1.96 = 0.12 (12% of threshold)
```

**Risk Mapping:**

```
0.234 < 1.47 → LOW RISK
```

**Response:**

```json
{
  "risk_check": {
    "risk_level": "low",
    "risk_score": 0.234,
    "can_proceed": true,
    "warnings": []
  }
}
```

**Frontend Action:** ✅ Proceed to confirm screen

---

### Scenario 2: Suspicious Transaction (Medium Risk)

**Input:**

```json
{
  "receiver_phone": "01798765432",
  "amount": 5000.0
}
```

**Features:**

- User has 5 previous transactions
- Average amount: 450 BDT (now sending 5000!)
- Receiver has 1 transaction (new account)
- Time: 11:30 PM (unusual hours)
- Amount: 10x higher than usual

**ML Processing:**

```
Reconstruction Error: 1.89
Threshold: 1.96
Ratio: 1.89 / 1.96 = 0.96 (96% of threshold)
```

**Risk Mapping:**

```
1.47 ≤ 1.89 < 2.94 → MEDIUM RISK
```

**Response:**

```json
{
  "risk_check": {
    "risk_level": "medium",
    "risk_score": 1.89,
    "can_proceed": true,
    "warnings": ["Transaction requires additional verification"]
  }
}
```

**Frontend Action:** ⚠️ Show warning dialog, allow proceed

---

### Scenario 3: Fraudulent Transaction (High Risk)

**Input:**

```json
{
  "receiver_phone": "01600000000",
  "amount": 50000.0
}
```

**Features:**

- User has 5 previous transactions
- Average amount: 450 BDT (now sending 50,000!)
- Receiver has 0 transactions (brand new account)
- Time: 3:45 AM (very unusual)
- Amount: 100x higher than usual

**ML Processing:**

```
Reconstruction Error: 4.56
Threshold: 1.96
Ratio: 4.56 / 1.96 = 2.33 (233% of threshold!)
```

**Risk Mapping:**

```
4.56 ≥ 2.94 → HIGH RISK
```

**Response:**

```json
{
  "risk_check": {
    "risk_level": "high",
    "risk_score": 4.56,
    "can_proceed": false,
    "warnings": [
      "Transaction flagged as high risk by fraud detection",
      "Unusual transaction pattern detected"
    ]
  }
}
```

**Frontend Action:** 🚫 Block transaction, show error dialog

---

## 🔐 Security Features

### 1. Double ML Check

```
Preview API → ML Check #1 → Show preview
                ↓
User confirms
                ↓
Confirm API → ML Check #2 → Execute transaction
```

**Why twice?**

- Prevents tampering between preview and confirm
- Catches changes in user behavior during delay
- Extra security layer

### 2. Risk-Based Blocking

| Risk Level | Can Proceed?          | Action                        |
| ---------- | --------------------- | ----------------------------- |
| Low        | ✅ Yes                | Auto-proceed                  |
| Medium     | ⚠️ Yes (with warning) | Require explicit confirmation |
| High       | 🚫 No                 | Block transaction             |

### 3. Transaction History Analysis

```python
# Uses last 30 days of transactions to establish baseline
sender_avg_amount = AVG(last_30_days_transactions)
sender_frequency = COUNT(last_30_days_transactions) / 30

# Flags deviation from normal pattern
if current_amount > sender_avg_amount * 10:
    # Likely anomaly
```

### 4. Receiver Validation

```python
# New receiver with no history → Higher risk
if receiver_tx_count == 0:
    # Extra scrutiny

# Receiver receiving many transfers → Possible money mule
if receiver_freq > 10:  # 10+ tx/day
    # Flag for review
```

---

## 🎓 How the Model Learns

### Training Process (not in current codebase, but how it was trained)

1. **Collect normal transactions** (non-fraudulent data)
2. **Extract 20 features** for each transaction
3. **Train autoencoder** to reconstruct these features
4. **Calculate threshold** (e.g., 95th percentile of reconstruction errors)
5. **Save model artifacts** (model.keras, scaler.pkl, encoders.pkl)

### Inference Process (what happens in production)

1. **New transaction arrives**
2. **Extract same 20 features**
3. **Pass through autoencoder**
4. **Calculate reconstruction error**
5. **Compare to threshold**
6. **Flag if error > threshold**

### Why Autoencoder?

- **Unsupervised Learning**: Doesn't need labeled fraud data
- **Pattern Recognition**: Learns what "normal" looks like
- **Anomaly Detection**: Anything deviating from normal is flagged
- **Adaptive**: Can be retrained as patterns change

---

## 📈 Monitoring & Tuning

### Adjustable Parameters

#### 1. Reconstruction Threshold

```python
# Environment variable or config
AUTOENCODER_THRESHOLD = 1.96  # Default

# Higher threshold = fewer false positives, more fraud may slip through
# Lower threshold = more false positives, catches more fraud
```

#### 2. Risk Level Boundaries

```python
# Current: 0.75x and 1.5x multipliers
# Can adjust based on business needs

LOW_THRESHOLD = threshold * 0.75      # 1.47
HIGH_THRESHOLD = threshold * 1.5      # 2.94
```

#### 3. Feature Importance

```python
# Can add/remove features based on analysis
# Current: 20 features
# Could expand to include:
# - Device fingerprint
# - IP geolocation
# - Transaction velocity (tx per hour)
# - Account age
```

### Metrics to Track

1. **False Positive Rate**: Normal transactions flagged as fraud
2. **False Negative Rate**: Fraud transactions missed
3. **Precision**: Of flagged transactions, how many were actually fraud?
4. **Recall**: Of actual fraud, how many were caught?

---

## 🚀 Future Enhancements

### Potential Improvements

1. **Real-time Model Updates**

   - Retrain model weekly/monthly
   - Adapt to new fraud patterns

2. **User Feedback Loop**

   - Allow users to report false positives
   - Improve model accuracy

3. **Additional Features**

   - Geolocation verification
   - Device fingerprinting
   - Biometric verification for high-risk transactions

4. **Multi-Model Ensemble**

   - Combine autoencoder with other ML models
   - XGBoost for classification
   - LSTM for sequence analysis

5. **Explainable AI**
   - Show users WHY transaction was flagged
   - Increase trust and transparency

---

## 📚 Summary

### Key Takeaways

1. **Autoencoder** learns normal transaction patterns
2. **Reconstruction error** measures how unusual a transaction is
3. **ML runs twice** (preview + confirm) for security
4. **Risk levels** (low/medium/high) guide user experience
5. **20 features** capture transaction, user, receiver, and temporal patterns
6. **Threshold (1.96)** balances security and usability

### Architecture Overview

```
User Input → Preview API → Feature Engineering → Autoencoder → Risk Level → Frontend Display
                                                                    ↓
                                                           User Confirmation
                                                                    ↓
User Confirm → Confirm API → ML Re-check → Transaction → Database → Success
```

### Files Involved

| File                              | Purpose                                         |
| --------------------------------- | ----------------------------------------------- |
| `send_entry_screen.dart`          | User input, preview API call                    |
| `send_confirm_screen.dart`        | Confirmation, confirm API call                  |
| `transaction_routes.py`           | API endpoints, feature building, ML integration |
| `src/utils/autoencoder_model.py`  | ML model loading and prediction                 |
| `autoencoder_anomaly_model.keras` | Trained neural network                          |
| `scaler.pkl`                      | Feature normalization                           |
| `label_encoders.pkl`              | Categorical encoding                            |

---

**End of Documentation** 🎉

For questions or issues, refer to the code comments or contact the development team.
