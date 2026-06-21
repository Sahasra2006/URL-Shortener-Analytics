from flask import Flask, render_template, request, redirect, Response
from database import conn, cursor
from user_agents import parse
import random
import string
import qrcode
import os
import csv

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def home():

    short_code = ""
    qr_image = ""

    if request.method == "POST":

        original_url = request.form["url"]
        custom_code = request.form.get("custom_code")

        if custom_code:
            short_code = custom_code
        else:
            short_code = ''.join(
                random.choices(
                    string.ascii_letters + string.digits,
                    k=6
                )
            )

        cursor.execute(
            "SELECT * FROM links WHERE short_code=%s",
            (short_code,)
        )
        existing = cursor.fetchone()

        if existing:
            return "Short Code Already Exists!"

        cursor.execute(
            "INSERT INTO links (user_id, original_url, short_code) VALUES (%s,%s,%s)",
            (1, original_url, short_code)
        )
        conn.commit()

        url = f"http://127.0.0.1:5000/{short_code}"

        img = qrcode.make(url)

        os.makedirs("static/qr", exist_ok=True)

        img.save(f"static/qr/{short_code}.png")

        qr_image = f"qr/{short_code}.png"

    # Dashboard Cards Data

    cursor.execute("SELECT COUNT(*) FROM links")
    total_links = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM clicks")
    total_clicks = cursor.fetchone()[0]

    cursor.execute("""
        SELECT country, COUNT(*) AS total
        FROM clicks
        GROUP BY country
        ORDER BY total DESC
        LIMIT 1
    """)
    top_country = cursor.fetchone()

    cursor.execute("""
        SELECT browser, COUNT(*) AS total
        FROM clicks
        GROUP BY browser
        ORDER BY total DESC
        LIMIT 1
    """)
    top_browser = cursor.fetchone()

    cursor.execute("""
        SELECT device, COUNT(*) AS total
        FROM clicks
        GROUP BY device
        ORDER BY total DESC
        LIMIT 1
    """)
    top_device = cursor.fetchone()

    return render_template(
        "index.html",
        short_code=short_code,
        qr_image=qr_image,
        total_links=total_links,
        total_clicks=total_clicks,
        top_country=top_country,
        top_browser=top_browser,
        top_device=top_device
    )


@app.route("/<short_code>")
def redirect_url(short_code):

    cursor.execute(
        "SELECT id, original_url FROM links WHERE short_code=%s",
        (short_code,)
    )

    result = cursor.fetchone()

    if result:

        link_id = result[0]
        original_url = result[1]

        user_agent = parse(request.headers.get("User-Agent"))

        browser = user_agent.browser.family

        if user_agent.is_mobile:
            device = "Mobile"
        elif user_agent.is_tablet:
            device = "Tablet"
        else:
            device = "Desktop"

    country = "India"

    cursor.execute("INSERT INTO clicks (link_id, browser, device, country) VALUES (%s,%s,%s,%s)",
    (link_id, browser, device, country)
)

    conn.commit()

    return redirect(original_url)

    return "URL not found"


@app.route("/analytics")
def analytics():

    search = request.args.get("search", "")

    cursor.execute("""
        SELECT l.id,
            l.short_code,
            l.original_url,
            COUNT(c.id) AS total_clicks
        FROM links l
        LEFT JOIN clicks c ON l.id = c.link_id
        WHERE l.short_code ILIKE %s
        GROUP BY l.id, l.short_code, l.original_url
        ORDER BY total_clicks DESC
    """, (f"%{search}%",))

    top_urls = cursor.fetchall()

    return render_template(
        "analytics.html",
        top_urls=top_urls
    )

@app.route("/export")
def export_csv():
    cursor.execute("""
        SELECT l.short_code,
            l.original_url,
            COUNT(c.id) AS total_clicks
        FROM links l
        LEFT JOIN clicks c
        ON l.id = c.link_id
        GROUP BY l.short_code, l.original_url
        ORDER BY total_clicks DESC
    """)
    rows = cursor.fetchall()
    def generate():
        yield "Short Code,Original URL,Total Clicks\n"
        for row in rows:
            yield f"{row[0]},{row[1]},{row[2]}\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=url_analytics.csv"
        }
    )

@app.route("/delete/<int:link_id>")
def delete_url(link_id):

    cursor.execute(
        "DELETE FROM links WHERE id = %s",
        (link_id,)
    )

    conn.commit()

    return redirect("/analytics")

@app.route("/visualizations")
def visualizations():

    # URL Analytics
    cursor.execute("""
        SELECT short_code, COUNT(c.id)
        FROM links l
        LEFT JOIN clicks c ON l.id = c.link_id
        GROUP BY short_code
        ORDER BY COUNT(c.id) DESC
    """)

    chart_data = cursor.fetchall()

    labels = [row[0] for row in chart_data]
    data = [row[1] for row in chart_data]

    # Browser Analytics
    cursor.execute("""
        SELECT browser, COUNT(*)
        FROM clicks
        GROUP BY browser
    """)
    browser_data = cursor.fetchall()

    browser_labels = [row[0] for row in browser_data]
    browser_counts = [row[1] for row in browser_data]

    # Device Analytics
    cursor.execute("""
        SELECT device, COUNT(*)
        FROM clicks
        GROUP BY device
    """)
    device_data = cursor.fetchall()

    device_labels = [row[0] for row in device_data]
    device_counts = [row[1] for row in device_data]

    # Country Analytics
    cursor.execute("""
        SELECT country, COUNT(*)
        FROM clicks
        GROUP BY country
    """)
    country_data = cursor.fetchall()

    country_labels = [row[0] for row in country_data]
    country_counts = [row[1] for row in country_data]

    return render_template(
        "visualizations.html",

        labels=labels,
        data=data,

        browser_labels=browser_labels,
        browser_counts=browser_counts,

        device_labels=device_labels,
        device_counts=device_counts,

        country_labels=country_labels,
        country_counts=country_counts
    )

if __name__ == "__main__":
    app.run(debug=True)