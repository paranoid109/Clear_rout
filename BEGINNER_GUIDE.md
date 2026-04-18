# 🗺️ AirRoute: Beginner's Guide 

Welcome to the AirRoute project! If you are new to coding or this project, don't worry. This guide translates all the complex technical jargon into simple, easy-to-understand concepts.

## 🤔 What does this project do?
Normally, maps (like Google Maps) give you the **fastest** route from Point A to Point B. But what if the fastest route forces you to walk through heavy traffic and bad smog? 

**AirRoute** is a smart map that finds two routes for you:
1. The **Fastest** route.
2. The **Cleanest** route (a small detour that keeps you away from bad air pollution).

It figures this out by grabbing live Air Quality Index (AQI) scores from the internet, predicting future pollution using AI, and applying those numbers directly onto street maps.

---

## 📁 Where is everything located? (Folder Breakdown)

Think of the project as a restaurant:
- The **Frontend** (`static/` folder) is the dining room where customers sit and look at the menu (the map and buttons).
- The **Backend** (`src/` folder) is the kitchen where all the actual heavy lifting and cooking (calculating math and fetching data) happens.
- The **Data** (`data/` folder) is the pantry where we store ingredients (maps and history logs).

Here is exactly what each main folder and file does:

### 1. `src/` (The Brain of the Operation)
This is where all the Python code lives.
- `main.py`: The Main Manager. If you start this file, the whole app turns on. It listens to the website and coordinates the other folders to get the job done.
- `routing/`: The Navigator. Uses map data to calculate your path over streets (`basic_router.py`) and decides if a detour is actually worth taking (`evaluator.py`).
- `prediction/`: The Fortune Teller. Contains `predictor.py`, an Artificial Intelligence (AI) script that looks at the time of day and the time of year to guess if the air will get cleaner or dirtier in the next few hours.
- `api/` & `sensors/`: The Gatherers. They go out to the internet (`aqi_service.py`) or physical hardware sensors (`aqi_sensor.py`) to ask, "What is the pollution level right now?"

### 2. `static/` (The Face of the App)
This is what the user actually sees on their screen.
- `index.html`: The skeleton of the web page.
- `style.css`: The paintbrush. It makes everything look pretty, adding dark mode, curved borders, and colors.
- `app.js`: The interactive tools. If a user drops a pin on the map or clicks the "Calculate" button, this file senses that click and yells at `main.py` to do the math.

### 3. `scripts/` (The Helpful Tools)
- `fetch_history.py`: A robot script that goes back in time and downloads the last 90 days of pollution data from the internet so our AI has something to learn from.

### 4. `data/` (The Storage Room)
- `air_quality_history.db`: A digital notebook. Every time we check the air or download history, we write it down here.
- `.graphml` files: These are massive text files that represent every single physical street, traffic light, and alleyway in the city (like **Bengaluru**).

---

## 🚀 First-Time Setup (On a New Windows Computer)

If you are setting this up on a brand-new Windows computer, you need to build the "kitchen" before you can cook! Here is a step-by-step guide explaining exactly what to click, where to type, and what the computer is doing behind the scenes.

### Step 1: Open your Command Prompt (The Black Screen)
1. On your Windows computer, click the **Start button** (the Windows logo) at the bottom left of your screen.
2. Type `cmd` into the search bar and press **Enter**. A black box with white text will pop up. This is your Command Prompt!
3. You need to tell the black box to go into your project folder. Type `cd` (which stands for "change directory"), press **Space**, and then drag and drop the `filter-rout` folder from your desktop right into the black box. Press **Enter**. (It will look something like `cd C:\Users\YourName\Documents\filter-rout`).

### Step 2: Create a Virtual Environment (The Safe Bubble)
We are going to create a "safe bubble" for python. This ensures that nothing we install messes up anything else on your computer.
- **Type this inside the black box and press Enter:**
  ```cmd
  python -m venv test_env
  ```
- **What is happening in the background?** The computer is silently building a brand-new, invisible folder named `test_env`. Inside this folder, it is placing a fresh, blank copy of Python that is completely isolated from the rest of your PC.

### Step 3: Enter the Bubble (Activation)
Now that the bubble is built, we have to actually step inside it.
- **Type this and press Enter:**
  ```cmd
  test_env\Scripts\activate
  ```
- **What is happening in the background?** Your Command Prompt will now magically show `(test_env)` at the very left of the typing line. This means you are officially inside the safe bubble! Any changes or downloads you make from now on will be trapped inside this specific folder.

### Step 4: Install the Required Tools (The Shopping List)
Our project relies on a lot of helpful toolkits built by other people (like `matplotlib` for graphs, or `osmnx` for downloading maps). Instead of downloading them one by one, we have a master "shopping list" called `requirements.txt`.
- **Type this and press Enter:**
  ```cmd
  pip install -r requirements.txt
  ```
- **What is happening in the background?** A package delivery robot named `pip` reads the text file, travels to the internet, finds every single tool listed, downloads them, and safely unpacks them inside your bubble. You will see a lot of loading bars scrolling by—this is completely normal!

### Step 5: Download the City Maps & AI History (Stocking the Pantry)
The code is completely ready, but the app has zero memory right now! It needs physical maps of Bengaluru and historical air pollution data so the Artificial Intelligence can start learning.
- **Type this and press Enter (wait a few seconds):**
  ```cmd
  python scripts/fetch_history.py
  ```
  *Background Check: This triggers a script that reaches out to an environmental weather service online. It downloads 90 straight days of hourly pollution data for Bengaluru and saves it into a local digital notebook (`air_quality_history.db`). The AI uses this later to predict the future!*

- **Next, type this and press Enter (Warning: Wait a few minutes!):**
  ```cmd
  python src/data/download_graph.py --place "Bengaluru, India" --base "data/bengaluru" --modes drive bike walk
  ```
  *Background Check: This grabs the location you typed ("Bengaluru") and reaches out to OpenStreetMap. It mathematically maps out every single crosswalk, highway, and alleyway in the city. It translates the entire physical city into millions of connectable dots and saves it to your computer so the routing math works instantly without needing the internet later on!*

---

## 🟢 How to Run It (Daily Use)

If you've already done the setup above, you only need one command to turn the app on!

```bash
# Wait for it to say "Application startup complete"
python src/main.py
```

1. Once it says `Application startup complete`, open your web browser (like Chrome or Safari).
2. Type `http://localhost:8000/` into the URL bar up top.
3. You will see the map! Click on the map to place two pins anywhere in Bengaluru, and click "Calculate Best Route". 

**That's it!** You are now using a complex AI-driven spatial map.
