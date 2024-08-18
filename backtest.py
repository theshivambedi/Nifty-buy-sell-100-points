import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

# Load the data
df = pd.read_csv('final.csv', parse_dates=['Date'])
df.set_index('Date', inplace=True)

# Ensure the data is sorted by date and time
df.sort_index(inplace=True)

# Constants
LOT_SIZE = 25
INITIAL_CAPITAL = 400000  # 4 lakh
CHARGES_PER_TRADE = 150
SLIPPAGE_PERCENT = 0.001  # 0.1%

# Function to calculate profit/loss including charges and slippage
def calculate_pnl(entry_price, exit_price, direction):
    entry_price_with_slippage = entry_price * (1 + SLIPPAGE_PERCENT) if direction == 'buy' else entry_price * (1 - SLIPPAGE_PERCENT)
    exit_price_with_slippage = exit_price * (1 - SLIPPAGE_PERCENT) if direction == 'buy' else exit_price * (1 + SLIPPAGE_PERCENT)

    if direction == 'buy':
        pnl = (exit_price_with_slippage - entry_price_with_slippage) * LOT_SIZE
    else:  # sell
        pnl = (entry_price_with_slippage - exit_price_with_slippage) * LOT_SIZE

    return round(pnl - (2 * CHARGES_PER_TRADE), 2)  # Charges for both entry and exit, rounded to 2 decimal places

# Initialize new columns
df['Trade_Signal'] = False
df['Trade_Exit'] = False
df['Trade_PnL'] = 0.0

# Process each day
for date, day_data in df.groupby(df.index.date):
    if len(day_data) == 0:
        continue

    # Get entry prices at 9:16
    entry_time = pd.Timestamp(date).replace(hour=9, minute=16)
    if entry_time in day_data.index:
        entry_price = day_data.loc[entry_time, 'Open']

        # Set trade signal
        df.loc[entry_time, 'Trade_Signal'] = True

        # Calculate stop loss prices
        buy_stop_loss = entry_price - 100
        sell_stop_loss = entry_price + 100

        # Check for stop loss or end of day exit
        buy_exit_price = entry_price
        sell_exit_price = entry_price
        exit_time = entry_time

        for time, row in day_data.loc[entry_time:].iterrows():
            if row['Low'] <= buy_stop_loss or row['High'] >= sell_stop_loss:
                buy_exit_price = max(row['Low'], buy_stop_loss)
                sell_exit_price = min(row['High'], sell_stop_loss)
                exit_time = time
                break
            elif time.time() >= pd.Timestamp('15:15').time():
                buy_exit_price = sell_exit_price = row['Close']
                exit_time = time
                break

        # Set exit signal
        df.loc[exit_time, 'Trade_Exit'] = True

        # Calculate combined P&L
        buy_pnl = calculate_pnl(entry_price, buy_exit_price, 'buy')
        sell_pnl = calculate_pnl(entry_price, sell_exit_price, 'sell')
        df.loc[exit_time, 'Trade_PnL'] = round(buy_pnl + sell_pnl, 2)

# Calculate cumulative P&L and account balance
df['Cumulative_PnL'] = df['Trade_PnL'].cumsum().round(2)
df['Account_Balance'] = (INITIAL_CAPITAL + df['Cumulative_PnL']).round(2)

# Calculate monthly returns
df['Month'] = df.index.to_period('M')
monthly_returns = df.groupby('Month').agg({
    'Trade_PnL': 'sum',
    'Account_Balance': 'last'
}).reset_index()

monthly_returns['Return_%'] = ((monthly_returns['Trade_PnL'] / INITIAL_CAPITAL) * 100).round(2)
monthly_returns['Cumulative_Return_%'] = (((monthly_returns['Account_Balance'] - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100).round(2)

# Print summary
print("Overall Strategy Performance:")
print(f"Total Trades: {df['Trade_Signal'].sum()}")
print(f"Total P&L: {df['Trade_PnL'].sum():.2f}")
print(f"Final Balance: {df['Account_Balance'].iloc[-1]:.2f}")
print(f"Overall Return %: {((df['Account_Balance'].iloc[-1] - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100):.2f}%")

print("\nMonthly Returns:")
print(monthly_returns.to_string(index=False))

# Save results to CSV
df.to_csv('strategy_results.csv')
monthly_returns.to_csv('monthly_returns.csv', index=False)

# Create charts
plt.figure(figsize=(12, 6))
plt.plot(df.index, df['Account_Balance'])
plt.title('Account Balance Over Time')
plt.xlabel('Date')
plt.ylabel('Balance (Rs)')
plt.grid(True)
plt.savefig('account_balance.png')
plt.close()

plt.figure(figsize=(12, 6))
plt.plot(monthly_returns['Month'].astype(str), monthly_returns['Return_%'])
plt.title('Monthly Returns')
plt.xlabel('Month')
plt.ylabel('Return (%)')
plt.xticks(rotation=45)
plt.grid(True)
plt.tight_layout()
plt.savefig('monthly_returns.png')
plt.close()

plt.figure(figsize=(12, 6))
plt.plot(monthly_returns['Month'].astype(str), monthly_returns['Cumulative_Return_%'])
plt.title('Cumulative Returns')
plt.xlabel('Month')
plt.ylabel('Cumulative Return (%)')
plt.xticks(rotation=45)
plt.grid(True)
plt.tight_layout()
plt.savefig('cumulative_returns.png')
plt.close()

# Drawdown analysis
df['Peak'] = df['Account_Balance'].cummax()
df['Drawdown'] = (df['Account_Balance'] - df['Peak']) / df['Peak'] * 100
max_drawdown = df['Drawdown'].min()

plt.figure(figsize=(12, 6))
plt.plot(df.index, df['Drawdown'])
plt.title(f'Drawdown Analysis (Max Drawdown: {max_drawdown:.2f}%)')
plt.xlabel('Date')
plt.ylabel('Drawdown (%)')
plt.grid(True)
plt.savefig('drawdown.png')
plt.close()

print(f"\nMax Drawdown: {max_drawdown:.2f}%")