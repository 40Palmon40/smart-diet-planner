from flask import Flask, request, jsonify
import requests, os, json, sys, logging
from datetime import datetime

app = Flask(__name__)
# Mark the start of a new session in the log
print("\n" + "=" * 60)
print("NEW FLASK SESSION STARTED:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 60 + "\n")


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


# Session banner
print("\n" + "=" * 60)
print(f"NEW FLASK SESSION STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60 + "\n")

# Save console logs to both screen and file
log_file = open("webhook_log.txt", "a", encoding="utf-8")



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

        # Get raw intent name and normalize it
        intent_info = (query_result.get("intent") or {})
        intent_raw = (intent_info.get("displayName") or "")
        intent = intent_raw.strip().lower()

        print("RAW INTENT NAME:", repr(intent_raw))
        print("NORMALIZED INTENT NAME:", repr(intent))

        # Parameters
        params = query_result.get("parameters") or {}

        # Cleaner console output
        query_text = (query_result.get("queryText") or "").strip()
        print("\n────────────── Dialogflow Request ──────────────")
        print("User said:", query_text)
        print("Intent:", intent)
        print("Parameters:", json.dumps(params, indent=2))
        print("────────────────────────────────────────────────\n")

        # Only handle our meal-planning / nutrition intents
        allowed_intents = {
            "meal plan request",
            "plan my breakfast",
            "nutrition info",
        }

        if intent not in allowed_intents:
            print("UNHANDLED INTENT:", repr(intent))
            return jsonify({"fulfillmentText": "I didn’t quite understand that."})

        # Helper: Dialogflow sometimes sends lists like ["breakfast"]
        def first_value(v):
            if isinstance(v, list):
                return v[0] if v else None
            return v

        # ---------- Nutrition Info Mode ----------
        if intent == "nutrition info":
            food_item = first_value(params.get("food")) or ""
            food_item = food_item.lower().strip()

            if not food_item:
                return jsonify({
                    "fulfillmentText": "What food would you like nutrition facts for?"
                })

            nutri_query = {
                "query": food_item,
                "apiKey": SPOONACULAR_API_KEY,
            }

            print("Nutrition query:", nutri_query)

            try:
                # Step 1: Search for ingredient ID
                search_resp = requests.get(
                    "https://api.spoonacular.com/food/ingredients/search",
                    params=nutri_query,
                    timeout=15,
                )
                search_data = search_resp.json() if search_resp.content else {}
                results = search_data.get("results") or []

                if not results:
                    return jsonify({
                        "fulfillmentText": (
                            f"Sorry, I couldn’t find nutrition data for {food_item}."
                        )
                    })

                ing_id = results[0].get("id")

                # Step 2: Get nutrition details for that ID
                info_resp = requests.get(
                    f"https://api.spoonacular.com/food/ingredients/{ing_id}/information",
                    params={"amount": 100, "unit": "g", "apiKey": SPOONACULAR_API_KEY},
                    timeout=15,
                )
                info = info_resp.json() if info_resp.content else {}

                name = info.get("name", food_item).title()
                nutrients = info.get("nutrition", {}).get("nutrients", [])

                # Extract common nutrients
                def get_nutrient(name_):
                    return next(
                        (n["amount"] for n in nutrients if n["name"] == name_),
                        None,
                    )

                calories = get_nutrient("Calories")
                protein = get_nutrient("Protein")
                carbs = get_nutrient("Carbohydrates")
                fat = get_nutrient("Fat")

                reply = (
                    f"🍎 Nutrition Facts for **{name}** (per 100g):\n\n"
                    f"• Calories: {calories} kcal\n"
                    f"• Protein: {protein} g\n"
                    f"• Carbs: {carbs} g\n"
                    f"• Fat: {fat} g\n\n"
                    f"Ask me about another food anytime!"
                )
                return jsonify({"fulfillmentText": reply})

            except Exception as e:
                print("Nutrition error:", e)
                return jsonify({
                    "fulfillmentText": (
                        f"Sorry, I couldn’t retrieve nutrition details for {food_item} right now."
                    )
                })

        # ---------- Extract raw values for meal-planning ----------
        raw_meal = first_value(params.get("mealType"))
        raw_diet = first_value(params.get("diet"))
        raw_number = first_value(params.get("number"))
        raw_time = first_value(params.get("maxTime"))

        # Fix empty-array / empty-string issue
        if raw_number in (None, [], ""):
            raw_number = 3           # default 3 items
        if raw_meal in (None, [], ""):
            raw_meal = "meal"        # default generic meal
        if raw_time in (None, [], ""):
            raw_time = None          # no time limit

        # ---------- Normalize values ----------
        meal_type = (raw_meal or "meal").lower()
        diet = (raw_diet or "").lower() or None

        try:
            number = int(raw_number)
        except (TypeError, ValueError):
            number = 3

        try:
            max_time = int(raw_time) if raw_time is not None else None
        except (TypeError, ValueError):
            max_time = None

        print("Normalized meal_type:", meal_type)
        print("Normalized diet:", diet)
        print("Normalized number:", number)
        print("Normalized max_time:", max_time)

        # ---------- Weekly 7-day mode ----------
        query_text_l = (query_text or "").lower()
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
            weekly_query = {
                "number": max(7, number),
                "apiKey": SPOONACULAR_API_KEY,
                "type": "main course",
            }
            if diet:
                weekly_query["diet"] = diet

            print("Weekly query:", weekly_query)

            resp = requests.get(
                "https://api.spoonacular.com/recipes/complexSearch",
                params=weekly_query,
                timeout=15,
            )
            data = resp.json() if resp.content else {}
            print("Weekly status:", resp.status_code)

            results = data.get("results") or []

            if not results:
                diet_part = f"{diet} " if diet else ""
                return jsonify({
                    "fulfillmentText": (
                        f"Sorry, I couldn’t generate a {diet_part}7-day meal plan right now. "
                        f"Please try again later."
                    )
                })

            # Label days
            results = results[:7]
            lines = []
            for i, item in enumerate(results, start=1):
                title = item.get("title", "a recipe")
                lines.append(f"Day {i}: {title}")

            diet_part = f"{diet} " if diet else ""
            reply_lines = [f"🍽️ {day}" for day in lines]

            reply = (
                f"🌿 Here’s your 7-day {diet_part}meal plan (dinners):\n\n"
                + "\n".join(reply_lines)
                + "\n\n✨ Ask me for a grocery list or nutrition facts for any of these!"
            )
            return jsonify({"fulfillmentText": reply})

        # ---------- Normal (non-weekly) recipe search ----------
        spoon_type = (meal_type or "").lower()
        if spoon_type in ("meal", "meals", ""):
            spoon_type = "main course"
        elif spoon_type in ("lunch", "dinner"):
            spoon_type = "main course"

        query = {
            "type": spoon_type,
            "number": number,
            "apiKey": SPOONACULAR_API_KEY,
        }
        if diet:
            query["diet"] = diet
        if max_time:
            query["maxReadyTime"] = max_time

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
            lower_meal_type = (meal_type or spoon_type or "meal").lower()

            if diet and diet not in lower_meal_type:
                diet_part = f"{diet} "
            else:
                diet_part = ""

            if max_time:
                label = "minute" if max_time == 1 else "minutes"
                time_part = f" under {max_time} {label}"
            else:
                time_part = ""

            msg = (
                f"😕 Sorry, I couldn’t find any {diet_part}{lower_meal_type}{time_part} ideas right now.\n"
                f"💡 Try asking for something like:\n"
                f"• 3 vegan dinners\n"
                f"• healthy breakfast ideas\n"
                f"• 5 low-carb snacks"
            )
            return jsonify({"fulfillmentText": msg})

        results = results[:number]
        lines = []
        for item in results:
            title = item.get("title", "a recipe")
            lines.append(f"🍽️ {title}")

        if diet and diet not in (meal_type or "").lower():
            diet_part = f"{diet} "
        else:
            diet_part = ""

        if max_time:
            label = "minute" if max_time == 1 else "minutes"
            time_part = f" under {max_time} {label}"
        else:
            time_part = ""

        reply = (
            f"🌿 Here are some {diet_part}{meal_type}{time_part} ideas:\n\n"
            + "\n".join(lines)
            + "\n\n✨ Let me know if you want grocery lists or nutrition facts too!"
        )
        return jsonify({"fulfillmentText": reply})

    except Exception as e:
        print("Error in webhook:", e)
        return jsonify({
            "fulfillmentText": "Sorry, something went wrong in the meal planner webhook."
        })



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)