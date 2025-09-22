from flask import Flask, request, jsonify, render_template
import yfinance as yf
import requests
from datetime import datetime, timedelta
import os

import streamlit as st

st.title("My First Streamlit App 🚀")
st.write("Hello, world! This is running on Streamlit.")


# News API Key
NEWS_API_KEY = "2567749225fc4909a01c07eb408eb458"


def fetch_stock_news(query):
    """Fetch latest stock news from NewsAPI"""
    try:
        url = (
            f"https://newsapi.org/v2/everything?"
            f"q={query}%20stock%20OR%20{query}%20earnings%20OR%20{query}%20financial&"
            f"sortBy=publishedAt&language=en&"
            f"domains=reuters.com,bloomberg.com,cnbc.com,marketwatch.com,yahoo.com&"
            f"apiKey={NEWS_API_KEY}"
        )

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "ok":
            return []

        articles = data.get("articles", [])
        latest_news = []
        seen_titles = set()
        seen_urls = set()

        for item in articles[:20]:
            title = item.get("title", "").strip()
            link = item.get("url")
            source = item.get("source", {}).get("name", "Unknown")
            description = item.get("description", "")
            published_at = item.get("publishedAt", "")

            # Skip duplicates and low-quality articles
            if (not title or not link or title in seen_titles or
                    link in seen_urls or title.lower() == "[removed]" or
                    not description):
                continue

            # Format the published date
            try:
                pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                formatted_date = pub_date.strftime("%b %d, %Y")
            except:
                formatted_date = "Recent"

            seen_titles.add(title)
            seen_urls.add(link)

            latest_news.append({
                "title": title,
                "link": link,
                "source": source,
                "description": description[:150] + "..." if len(description) > 150 else description,
                "published_at": formatted_date
            })

            if len(latest_news) >= 5:
                break

        return latest_news

    except Exception as e:
        print(f"Error fetching news: {str(e)}")
        return []


def analyze_stock(ticker_info, current_price, history_data):
    """Enhanced AI analysis of stock"""
    try:
        pe_ratio = ticker_info.get("trailingPE")
        market_cap = ticker_info.get("marketCap", 0)

        # Price trend analysis
        prices = list(history_data.values())
        if len(prices) >= 2:
            price_change = ((prices[-1] - prices[0]) / prices[0]) * 100
            trend = "📈 Upward" if price_change > 2 else "📉 Downward" if price_change < -2 else "➡️ Sideways"
        else:
            price_change = 0
            trend = "➡️ Neutral"

        # Build analysis
        analysis_parts = []

        # Valuation analysis
        if pe_ratio and pe_ratio != "N/A":
            if pe_ratio < 15:
                analysis_parts.append("Potentially undervalued (low P/E)")
            elif pe_ratio > 25:
                analysis_parts.append("May be overvalued (high P/E)")
            else:
                analysis_parts.append("Fairly valued")

        # Trend analysis
        analysis_parts.append(f"{trend} trend ({price_change:+.1f}% period)")

        # Market cap category
        if market_cap > 200_000_000_000:
            analysis_parts.append("Large-cap stock")
        elif market_cap > 10_000_000_000:
            analysis_parts.append("Mid-cap stock")
        elif market_cap > 0:
            analysis_parts.append("Small-cap stock")

        return " | ".join(analysis_parts)

    except Exception as e:
        return "Basic analysis available - consult financial advisor for investment decisions"


app = Flask(__name__)


@app.route("/")
def index():
    """Serve the main HTML page"""
    return render_template("index.html")


@app.route("/get_stock_data", methods=["POST"])
def get_stock_data():
    """Main endpoint to fetch stock data"""
    try:
        data = request.json
        ticker = data.get("ticker", "").upper().strip()

        if not ticker:
            return jsonify({"error": "Please provide a valid ticker symbol"})

        print(f"Fetching data for ticker: {ticker}")

        # Fetch stock data
        stock = yf.Ticker(ticker)

        # Get current price and basic info
        hist_1d = stock.history(period="1d")
        if hist_1d.empty:
            return jsonify({"error": f"No data found for ticker '{ticker}'. Please check the symbol."})

        current_price = hist_1d["Close"].iloc[-1]

        # Get company info
        info = stock.info
        company_name = info.get("longName", info.get("shortName", ticker))

        # Financial metrics
        pe_ratio = info.get("trailingPE")
        if pe_ratio and pe_ratio != "N/A":
            pe_ratio = round(pe_ratio, 2)
        else:
            pe_ratio = "N/A"

        market_cap = info.get("marketCap")
        if market_cap:
            if market_cap >= 1_000_000_000_000:
                market_cap_display = f"${market_cap / 1_000_000_000_000:.2f}T"
            elif market_cap >= 1_000_000_000:
                market_cap_display = f"${market_cap / 1_000_000_000:.2f}B"
            elif market_cap >= 1_000_000:
                market_cap_display = f"${market_cap / 1_000_000:.2f}M"
            else:
                market_cap_display = f"${market_cap:,.0f}"
        else:
            market_cap_display = "N/A"

        # Get default 7-day history
        history = stock.history(period="7d")["Close"]
        history_dict = {str(k.date()): round(v, 2) for k, v in history.items()}

        # Enhanced AI analysis
        ai_advice = analyze_stock(info, current_price, history_dict)

        # Fetch news
        news = fetch_stock_news(f"{ticker} {company_name}")

        # Additional metrics
        day_change = info.get("regularMarketChange", 0)
        day_change_percent = info.get("regularMarketChangePercent", 0)

        if day_change_percent:
            day_change_percent = day_change_percent * 100

        response_data = {
            "ticker": ticker,
            "company_name": company_name,
            "price": round(current_price, 2),
            "day_change": round(day_change, 2) if day_change else 0,
            "day_change_percent": round(day_change_percent, 2) if day_change_percent else 0,
            "pe_ratio": pe_ratio,
            "market_cap": market_cap_display,
            "history": history_dict,
            "advice": ai_advice,
            "news": news,
            "currency": info.get("currency", "USD"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A")
        }

        print(f"Returning data for {ticker}: {len(history_dict)} price points, {len(news)} news items")
        return jsonify(response_data)

    except Exception as e:
        print(f"Error in get_stock_data: {str(e)}")
        error_msg = str(e)
        if "No data found" in error_msg or "not found" in error_msg.lower():
            return jsonify({"error": f"Ticker '{ticker}' not found. Please verify the symbol."})
        else:
            return jsonify({"error": f"Error retrieving data: {error_msg}"})


@app.route("/get_chart_data", methods=["POST"])
def get_chart_data():
    """Endpoint to fetch chart data for different time periods"""
    try:
        data = request.json
        ticker = data.get("ticker", "").upper().strip()
        period = data.get("period", "7d")

        print(f"Chart data request: ticker={ticker}, period={period}")

        if not ticker:
            return jsonify({"error": "Please provide a valid ticker symbol"})

        # Fetch stock data
        stock = yf.Ticker(ticker)

        # Period mapping for yfinance
        period_mapping = {
            "7d": "7d",
            "1m": "1mo",
            "3m": "3mo",
            "6m": "6mo",
            "1y": "1y",
            "5y": "5y"
        }

        yf_period = period_mapping.get(period, "7d")
        print(f"Using yfinance period: {yf_period}")

        # Get historical data
        history = stock.history(period=yf_period)["Close"]

        if history.empty:
            return jsonify({"error": f"No chart data available for {ticker} with period {period}"})

        # Format history data
        history_dict = {str(k.date()): round(v, 2) for k, v in history.items()}

        print(f"Returning {len(history_dict)} data points for {ticker}")

        return jsonify({
            "ticker": ticker,
            "period": period,
            "history": history_dict,
            "status": "success"
        })

    except Exception as e:
        print(f"Error in get_chart_data: {str(e)}")
        return jsonify({"error": f"Error retrieving chart data: {str(e)}"})


@app.route("/health")
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    port = int(os.getenv("PORT", 5000))
    app.run(debug=debug_mode, host="0.0.0.0", port=port)