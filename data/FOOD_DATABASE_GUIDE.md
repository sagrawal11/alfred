# 📝 Food Database Guide

## How to Add Your Foods

Edit the file `data/wu_foods.json` to add your foods. The system will automatically recognize them!

### Food Format

The database is organized by **restaurant name** as the top-level key. Each restaurant contains all the foods you eat from that restaurant:

```json
{
  "restaurant_name": {
    "food_name": {
      "calories": 500,
      "protein": 30,
      "carbs": 50,
      "fat": 20,
      "fiber": 5,
      "serving_size": "1 serving",
      "common_servings": ["1/2 serving", "1 serving", "2 servings"]
    }
  }
}
```

### Example: Adding "Sazon Quesadilla" and "Krafthouse Quesadilla"

Since the same food can have different macros at different restaurants, organize by restaurant:

```json
{
  "sazon": {
    "quesedilla": {
      "calories": 1060,
      "protein": 36,
      "carbs": 116,
      "fat": 47,
      "fiber": 9,
      "serving_size": "3 pieces",
      "common_servings": ["1 piece", "2 pieces", "3 pieces"]
    }
  },
  "krafthouse": {
    "quesedilla": {
      "calories": 980,
      "protein": 32,
      "carbs": 108,
      "fat": 42,
      "fiber": 8,
      "serving_size": "3 pieces",
      "common_servings": ["1 piece", "2 pieces", "3 pieces"]
    }
  }
}
```

### How It Works

When you text **"I ate a sazon quesedilla"**, the system will:
1. Recognize "sazon" as the restaurant
2. Recognize "quesedilla" as the food
3. Look up `sazon.quesedilla` in the database
4. Log the macros: 1060 cal, 36g protein, 116g carbs, 47g fat

If you text **"I ate a krafthouse quesedilla"**, it will find the different macros from the `krafthouse` restaurant.

### Field Descriptions

- **calories**: Total calories per serving
- **protein**: Protein in grams per serving
- **carbs**: Carbohydrates in grams per serving
- **fat**: Fat in grams per serving
- **fiber**: Fiber in grams per serving (optional)
- **serving_size**: Description of the base serving (e.g., "3 pieces", "1 bowl")
- **common_servings**: List of common serving phrases (optional, helps with portion multipliers)

### Portion Multipliers

The system automatically handles portion multipliers:
- **"half a sazon quesedilla"** → 0.5x the macros
- **"2 sazon quesedillas"** → 2x the macros
- **"double sazon quesedilla"** → 2x the macros

### Restaurant Names

Use lowercase, no spaces. Common restaurant names in the database:
- `sazon`
- `krafthouse`
- `gsoy`
- `il_forno`
- `farmstead`
- `skillet`
- `kraft`
- `gothic`
- `pitch`
- `mcdonalds`
- `cafe`
- `tandoor`
- `zwellis`

### Food Names

Use lowercase with underscores for multi-word foods:
- `quesedilla` (not "quesadilla" - use your spelling)
- `grilled_chicken`
- `chicken_tikka`
- `mac_and_cheese`

### Tips

1. **Be consistent**: Use the same restaurant name spelling everywhere
2. **Test matching**: Try various phrasings like "sazon quesedilla", "quesedilla from sazon", "ate sazon quesedilla"
3. **Add variations**: The system creates lookup keys like "sazon quesedilla" and "quesedilla sazon" automatically
4. **Check JSON syntax**: Make sure your JSON is valid (no trailing commas, proper quotes)

### Current Restaurants

The database currently includes these restaurants with sample foods:
- **sazon**: quesedilla, burrito, bowl
- **krafthouse**: quesedilla, burger
- **gsoy**: chicken_teriyaki, beef_bowl
- **il_forno**: pizza_slice, pasta
- **farmstead**: grilled_chicken, salmon
- **skillet**: omelette, pancakes
- **kraft**: mac_and_cheese, grilled_cheese
- **gothic**: burger, fries
- **pitch**: pizza_slice, wings
- **mcdonalds**: big_mac, fries
- **cafe**: sandwich, salad
- **tandoor**: chicken_tikka, naan
- **zwellis**: sandwich, wrap

Replace the sample foods with your actual foods and macros!
