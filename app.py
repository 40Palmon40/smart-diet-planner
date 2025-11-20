from flask import Flask, request, jsonify
import requests, os, json, sys, logging
from datetime import datetime

app = Flask(__name__)
# Mark the start of a new session in the log
print("\n" + "=" * 60)
print("NEW FLASK SESSION STARTED:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 60 + "\n")

app = Flask(__name__)

# Log to console AND file
import logging, sys
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.__stdout__),                 # console
        logging.FileHandler("webhook_log.txt", encoding="utf-8")  # file
    ],
)
log = logging.getLogger(__name__)
print = log.info  # redirect print() → log.info()

# Session banner
print("\n" + "=" * 60)
print(f"NEW FLASK SESSION STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60 + "\n")

# Save console logs to both screen and file
log_file = open("webhook_log.txt", "a", encoding="utf-8")
sys.stdout = log_file
sys.stderr = log_file


# 🔑 Put your real Spoonacular API key between the quotes:
SPOONACULAR_API_KEY = "65bf474036f44c66b32c899120309ca0"


@app.get("/health")
def health():
    return {"status": "ok"}


def first_value(v):
    """Dialogflow sometimes sends lists like ['breakfasts'] – this picks the first."""
    if isinstance(v, list):
        return v[0] if v else None
    return v
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # Get JSON from Dialogflow
        req = request.get_json(silent=True) or {}
        query_result = req.get("queryResult") or {}
        intent = (query_result.get("intent") or {}).get("displayName", "")
        params = query_result.get("parameters") or {}

        # Cleaner console output
        query_text = (query_result.get("queryText") or "").strip()
        print("\n────────────── Dialogflow Request ──────────────")
        print("Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print(f"User said: {query_text}")
        print(f"Intent: {intent}")
        print("Parameters:", json.dumps(params, indent=2))
        print("────────────────────────────────────────────────\n")

        # (These lines are a bit redundant but harmless; you can remove them later if you want)
        query_result = req.get("queryResult") or {}
        intent = (query_result.get("intent") or {}).get("displayName", "")
        params = query_result.get("parameters") or {}

        print("Intent:", intent)
        print("Params:", params)

        # Only handle our meal-planning intent(s)
        allowed_intents = {"Meal Plan Request", "Plan my breakfast"}
        if intent not in allowed_intents:
            return jsonify({"fulfillmentText": "I didn’t quite understand that."})

        # Extract raw values (may be lists from Dialogflow)
        raw_meal = first_value(params.get("mealType"))
        raw_diet = first_value(params.get("diet"))
        raw_number = first_value(params.get("number"))
        raw_time = first_value(params.get("maxTime"))

        # Normalize meal type (handle plurals like "breakfasts" → "breakfast")
        meal_type = (raw_meal or "breakfast").lower()
        if meal_type.endswith("es") and meal_type[:-2] in ("lunch",):
            meal_type = meal_type[:-2]
        elif meal_type.endswith("s"):
            meal_type = meal_type[:-1]

        # Normalize diet
        diet = (raw_diet or "").lower() or None

        # If diet is empty but meal_type contains a known diet word, split it.
        known_diets = ["keto", "vegan", "vegetarian", "paleo"]
        if not diet:
            for d in known_diets:
                prefix = d + " "
                if meal_type.startswith(prefix):
                    diet = d
                    meal_type = meal_type[len(prefix):]  # "keto lunch" -> "lunch"
                    break

        # Normalize number
        try:
            number = int(raw_number) if raw_number is not None else 3
        except (TypeError, ValueError):
            number = 3

        # Normalize max cooking time (minutes)
        try:
            max_time = int(raw_time) if raw_time is not None else None
        except (TypeError, ValueError):
            max_time = None

        print("Normalized meal_type:", meal_type)
        print("Normalized diet:", diet)
        print("Normalized number:", number)
        print("Normalized max_time:", max_time)

        # --- Weekly plan mode: e.g., "make a 7 day (vegan) meal plan" ---
        query_text_l = (query_text or "").lower()

        # Consider it a "generic meal" request if they didn't say breakfast/lunch/dinner/snack,
        # or if the word "meal" appears.
        lower_meal_type = (meal_type or "").lower()
        generic_meal = (
            lower_meal_type in ("meal", "", None)
            or "meal" in lower_meal_type
        )

        weekly_mode = (
            (generic_meal and number >= 7)
            or "meal plan" in query_text_l
            or "7 day" in query_text_l
            or "7-day" in query_text_l
            or "week" in query_text_l
        )

        if weekly_mode:
            plan_query = {"timeFrame": "week", "apiKey": SPOONACULAR_API_KEY}
            if diet:
                plan_query["diet"] = diet  # vegan/vegetarian/keto/etc.

            print("Weekly plan query:", plan_query)

            resp = requests.get(
                "https://api.spoonacular.com/mealplanner/generate",
                params=plan_query,
                timeout=20,
            )
            data = resp.json() if resp.content else {}
            print("Weekly plan status:", resp.status_code)

            week = data.get("week") or {}
            if not week:
                # Clean diet word
                if diet and diet not in ("meal", "dinner", "lunch", "breakfast"):
                    diet_part = f"{diet} "
                else:
                    diet_part = ""
                return jsonify({
                    "fulfillmentText": f"Sorry, I couldn’t generate a {diet_part}7-day meal plan right now. Try again in a moment."
                })

            # Build a 7-day dinner plan, labeled by day and try to avoid duplicates
            order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            day_labels = ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"]

            lines = []
            seen_titles = set()

            for idx, day_name in enumerate(order):
                day = week.get(day_name, {}) or {}
                meals = day.get("meals") or []

                # Try to pick a "dinner" first
                pick = next((m for m in meals if "dinner" in (m.get("title", "").lower())), None)

                # Fallback: 3rd meal if present
                if not pick and len(meals) >= 3:
                    pick = meals[2]
                # Fallback: last meal
                if not pick and meals:
                    pick = meals[-1]

                if not pick:
                    continue

                title = pick.get("title", "a recipe")

                # Try to avoid exact duplicates across days
                if title in seen_titles:
                    continue
                seen_titles.add(title)

                label = day_labels[idx]
                lines.append(f"{label}: {title}")

            # Clean diet part for the weekly reply
            if diet and diet not in ("meal", "dinner", "lunch", "breakfast"):
                diet_part = f"{diet} "
            else:
                diet_part = ""

            if lines:
                reply = (
                    f"Here’s a 7-day {diet_part}meal plan (dinners):\n"
                    + "\n".join(lines)
                )
            else:
                reply = (
                    f"Here’s your 7-day {diet_part}meal plan. "
                    "(I can list full days if you’d like.)"
                )

            return jsonify({"fulfillmentText": reply})

        # ---------------- Normal (non-weekly) recipe search ----------------

        # Build request to Spoonacular
        query = {
            "type": meal_type,          # breakfast / lunch / dinner / snack
            "number": number,
            "apiKey": SPOONACULAR_API_KEY,
        }
        if diet:
            query["diet"] = diet       # vegan, vegetarian, etc.
        if max_time:
            query["maxReadyTime"] = max_time  # under X minutes

        print("Spoonacular query:", query)

        r = requests.get(
            "https://api.spoonacular.com/recipes/complexSearch",
            params=query,
            timeout=15,
        )
        data = r.json() if r.content else {}
        print("Spoonacular status:", r.status_code)

        results = data.get("results") or []

        if not results:
            # Clean diet word
            lower_meal_type = (meal_type or "").lower()
            if diet and diet not in lower_meal_type:
                diet_part = f"{diet} "
            else:
                diet_part = ""

            if max_time:
                label = "minute" if max_time == 1 else "minutes"
                time_part = f" under {max_time} {label}"
            else:
                time_part = ""

            return jsonify({
                "fulfillmentText": f"I couldn’t find any {diet_part}{meal_type}{time_part} recipes right now. Try a different meal type, diet, or time."
            })

        # Limit to the number requested
        results = results[:number]
        titles = ", ".join(item.get("title", "a recipe") for item in results)

        # Avoid "vegan vegan meal" style duplication
        lower_meal_type = (meal_type or "").lower()
        if diet and diet not in lower_meal_type:
            diet_part = f"{diet} "
        else:
            diet_part = ""

        if max_time:
            label = "minute" if max_time == 1 else "minutes"
            time_part = f" under {max_time} {label}"
        else:
            time_part = ""

        reply = f"Here are some {diet_part}{meal_type}{time_part} ideas: {titles}"

        return jsonify({"fulfillmentText": reply})

    except Exception as e:
        print("Error in webhook:", e)
        return jsonify({
            "fulfillmentText": "Sorry, something went wrong in the meal planner webhook."
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
