from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import csv
import io

app = Flask(__name__)

# Home
@app.route('/')
def home():
    return render_template('index.html')

# Add Trade
@app.route('/add', methods=['GET', 'POST'])
def add_trade():
    if request.method == 'POST':
        symbol = request.form['symbol']
        date = request.form['date']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])
        trade_type = request.form['trade_type']

        conn = sqlite3.connect('trades.db')
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                date TEXT,
                quantity INTEGER,
                price REAL,
                trade_type TEXT
            )
        ''')
        c.execute("INSERT INTO trades (symbol, date, quantity, price, trade_type) VALUES (?, ?, ?, ?, ?)",
                  (symbol, date, quantity, price, trade_type))
        conn.commit()
        conn.close()

        return redirect(url_for('view_trades'))

    return render_template('add_trade.html')


# View Trades
@app.route('/trades')
def view_trades():
    conn = sqlite3.connect('trades.db')
    c = conn.cursor()

    c.execute("SELECT * FROM trades ORDER BY date DESC")
    trades = c.fetchall()

    c.execute("SELECT SUM(quantity * price) FROM trades WHERE trade_type = 'Buy'")
    total_buy = c.fetchone()[0] or 0

    c.execute("SELECT SUM(quantity * price) FROM trades WHERE trade_type = 'Sell'")
    total_sell = c.fetchone()[0] or 0

    total_pnl = total_sell - total_buy
    total_trades = len(trades)

    # Cumulative P&L
    c.execute("SELECT date, trade_type, quantity, price FROM trades ORDER BY date")
    rows = c.fetchall()
    pnl_data = []
    cumulative = 0

    for row in rows:
        date, ttype, qty, price = row
        if ttype.lower() == 'buy':
            cumulative -= qty * price
        elif ttype.lower() == 'sell':
            cumulative += qty * price
        pnl_data.append({'date': date, 'pnl': round(cumulative, 2)})

    # Advanced Analytics
    c.execute("SELECT quantity, price, trade_type FROM trades")
    win = 0
    loss = 0
    profits = []

    for q, p, ttype in c.fetchall():
        value = q * p
        if ttype.lower() == 'sell':
            profits.append(value)
            win += 1
        else:
            profits.append(-value)
            loss += 1

    avg_pnl = round(sum(profits) / len(profits), 2) if profits else 0
    max_profit = round(max(profits), 2) if profits else 0
    max_loss = round(min(profits), 2) if profits else 0
    win_rate = round((win / total_trades) * 100, 2) if total_trades else 0

    conn.close()

    return render_template(
        'trades.html',
        trades=trades,
        total_trades=total_trades,
        total_buy=total_buy,
        total_sell=total_sell,
        total_pnl=total_pnl,
        pnl_data=pnl_data,
        win_rate=win_rate,
        avg_pnl=avg_pnl,
        max_profit=max_profit,
        max_loss=max_loss
    )

# Edit Trade
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_trade(id):
    conn = sqlite3.connect('trades.db')
    c = conn.cursor()

    if request.method == 'POST':
        symbol = request.form['symbol']
        date = request.form['date']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])
        trade_type = request.form['trade_type']

        c.execute("""
            UPDATE trades SET symbol = ?, date = ?, quantity = ?, price = ?, trade_type = ?
            WHERE id = ?
        """, (symbol, date, quantity, price, trade_type, id))

        conn.commit()
        conn.close()
        return redirect(url_for('view_trades'))

    c.execute("SELECT * FROM trades WHERE id = ?", (id,))
    trade = c.fetchone()
    conn.close()
    return render_template('edit_trade.html', trade=trade)


# Delete Trade
@app.route('/delete/<int:id>')
def delete_trade(id):
    conn = sqlite3.connect('trades.db')
    c = conn.cursor()
    c.execute("DELETE FROM trades WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_trades'))


# Upload CSV
@app.route('/upload', methods=['GET', 'POST'])
def upload_csv():
    if request.method == 'POST':
        file = request.files['file']
        if not file:
            return "No file uploaded", 400

        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.reader(stream)
        next(csv_input)  # Skip header

        conn = sqlite3.connect('trades.db')
        c = conn.cursor()

        for row in csv_input:
            if len(row) < 5:
                continue
            symbol, date, quantity, price, trade_type = row
            try:
                c.execute("""
                    INSERT INTO trades (symbol, date, quantity, price, trade_type)
                    VALUES (?, ?, ?, ?, ?)
                """, (symbol, date, int(quantity), float(price), trade_type))
            except Exception as e:
                print("Error inserting row:", row, e)

        conn.commit()
        conn.close()
        return redirect(url_for('view_trades'))

    return render_template('upload.html')


if __name__ == '__main__':
    app.run(debug=True)
