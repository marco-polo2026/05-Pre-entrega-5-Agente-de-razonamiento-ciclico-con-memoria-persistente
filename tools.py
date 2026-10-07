from typing import Any

from langchain_core.tools import tool

RECIPES: dict[int, dict[str, Any]] = {
    1: {
        "name": "Chicken stir-fry",
        "minutes": 20,
        "ingredients": ["chicken", "bell pepper", "onion", "soy sauce", "garlic"],
        "steps": [
            "Cut the chicken and vegetables into strips.",
            "Stir-fry the chicken over high heat for 6 minutes.",
            "Add the vegetables and garlic, cook 5 more minutes.",
            "Add the soy sauce and serve.",
        ],
    },
    2: {
        "name": "Roast chicken with potatoes",
        "minutes": 75,
        "ingredients": ["chicken", "potato", "lemon", "rosemary", "olive oil"],
        "steps": [
            "Preheat the oven to 200°C.",
            "Season the chicken with lemon, rosemary and olive oil.",
            "Place it on a tray surrounded by sliced potatoes.",
            "Roast for 70 minutes.",
        ],
    },
    3: {
        "name": "Chicken milanesa",
        "minutes": 35,
        "ingredients": ["chicken", "egg", "breadcrumbs", "garlic", "parsley"],
        "steps": [
            "Flatten the chicken breasts.",
            "Dip them in beaten egg with garlic and parsley.",
            "Coat them in breadcrumbs.",
            "Fry or bake until golden.",
        ],
    },
    4: {
        "name": "Potato omelette",
        "minutes": 40,
        "ingredients": ["potato", "egg", "onion", "olive oil"],
        "steps": [
            "Fry the sliced potatoes and onion in olive oil.",
            "Mix them with beaten eggs.",
            "Cook in a pan on both sides.",
        ],
    },
}


@tool
async def search_recipes(ingredient: str) -> dict[str, Any]:
    """Search the recipe database for recipes that use a given ingredient.

    Returns only a summary of each recipe: its id, name and preparation time in
    minutes. It does NOT return ingredients or steps; to get those, call
    get_recipe_details with the recipe id.

    Args:
        ingredient: A single ingredient name in English, singular and lowercase,
            for example "chicken" or "potato". Translate it if the user wrote
            it in another language.
    """
    matches = [
        {"id": recipe_id, "name": recipe["name"], "minutes": recipe["minutes"]}
        for recipe_id, recipe in RECIPES.items()
        if ingredient in recipe["ingredients"]
    ]
    if not matches:
        return {"error": f"No recipes found for ingredient '{ingredient}'."}
    return {"recipes": matches}


@tool
async def get_recipe_details(recipe_id: int) -> dict[str, Any]:
    """Get the full details of one recipe: its ingredients and its steps.

    Use it after search_recipes, because it needs the numeric recipe id that
    search_recipes returns. It cannot search by name or by ingredient.

    Args:
        recipe_id: The numeric id of the recipe, as returned by search_recipes.
    """
    recipe = RECIPES.get(recipe_id)
    if recipe is None:
        return {"error": f"No recipe with id {recipe_id}. Use search_recipes to find valid ids."}
    return {"id": recipe_id, **recipe}
