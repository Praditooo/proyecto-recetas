[1mdiff --git a/app/routers/recipes.py b/app/routers/recipes.py[m
[1mindex 6388489..87de162 100644[m
[1m--- a/app/routers/recipes.py[m
[1m+++ b/app/routers/recipes.py[m
[36m@@ -80,7 +80,9 @@[m [mdef list_recipes([m
     q: str | None = Query(None, min_length=1, max_length=100, description="Buscar por nombre del plato"),[m
     difficulty: Difficulty | None = Query(None, description="Fácil, Media o Difícil"),[m
     min_rating: int | None = Query(None, ge=1, le=5, description="Solo recetas con al menos estas estrellas"),[m
[31m-    sort: Literal["recent", "rating"] = Query("recent", description="recent: más nuevas primero; rating: mejor calificadas"),[m
[32m+[m[32m    sort: Literal["recent", "oldest", "rating"] = Query([m
[32m+[m[32m        "recent", description="recent: más nuevas primero; oldest: más antiguas primero; rating: mejor calificadas"[m
[32m+[m[32m    ),[m
     limit: int = Query(50, ge=1, le=100),[m
     offset: int = Query(0, ge=0),[m
 ):[m
[36m@@ -100,10 +102,15 @@[m [mdef list_recipes([m
     total = db.scalar(select(func.count()).select_from(stmt.subquery()))[m
     response.headers["X-Total-Count"] = str(total)[m
 [m
[31m-    order = [func.coalesce(Rating.stars, 0).desc()] if sort == "rating" else [][m
[32m+[m[32m    if sort == "oldest":[m
[32m+[m[32m        order = [Recipe.created_at.asc(), Recipe.id.asc()][m
[32m+[m[32m    elif sort == "rating":[m
[32m+[m[32m        order = [func.coalesce(Rating.stars, 0).desc(), Recipe.created_at.desc(), Recipe.id.desc()][m
[32m+[m[32m    else:[m
[32m+[m[32m        order = [Recipe.created_at.desc(), Recipe.id.desc()][m
     # selectinload trae todas las calificaciones en una sola consulta (evita N+1 en _to_out).[m
     stmt = stmt.options(selectinload(Recipe.ratings))[m
[31m-    stmt = stmt.order_by(*order, Recipe.created_at.desc(), Recipe.id.desc()).limit(limit).offset(offset)[m
[32m+[m[32m    stmt = stmt.order_by(*order).limit(limit).offset(offset)[m
     return [_to_out(r, user.id) for r in db.scalars(stmt).all()][m
 [m
 [m
[36m@@ -125,6 +132,18 @@[m [mdef rate_recipe(recipe_id: int, data: RatingCreate, db: DbSession, user: Current[m
     return _to_out(recipe, user.id)[m
 [m
 [m
[32m+[m[32m@router.delete("/{recipe_id}/rating", response_model=RecipeOut)[m
[32m+[m[32mdef remove_rating(recipe_id: int, db: DbSession, user: CurrentUser):[m
[32m+[m[32m    """Quita la calificación del usuario; si no existía, no hace nada."""[m
[32m+[m[32m    recipe = _get_owned(db, user, recipe_id)[m
[32m+[m[32m    rating = next((r for r in recipe.ratings if r.user_id == user.id), None)[m
[32m+[m[32m    if rating is not None:[m
[32m+[m[32m        db.delete(rating)[m
[32m+[m[32m        db.commit()[m
[32m+[m[32m        db.refresh(recipe)[m
[32m+[m[32m    return _to_out(recipe, user.id)[m
[32m+[m
[32m+[m
 @router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)[m
 def delete_recipe(recipe_id: int, db: DbSession, user: CurrentUser):[m
     db.delete(_get_owned(db, user, recipe_id))[m
[1mdiff --git a/app/templates/dashboard.html b/app/templates/dashboard.html[m
[1mindex 8a1eeb4..fc7ac75 100644[m
[1m--- a/app/templates/dashboard.html[m
[1m+++ b/app/templates/dashboard.html[m
[36m@@ -92,6 +92,7 @@[m
       <label><span class="visually-hidden">Ordenar por</span>[m
         <select name="sort">[m
           <option value="recent">Más recientes</option>[m
[32m+[m[32m          <option value="oldest">Más antiguas</option>[m
           <option value="rating">Mejor calificadas</option>[m
         </select>[m
       </label>[m
[1mdiff --git a/tests/test_recipes_api.py b/tests/test_recipes_api.py[m
[1mindex 74ea7bb..c26f1eb 100644[m
[1m--- a/tests/test_recipes_api.py[m
[1m+++ b/tests/test_recipes_api.py[m
[36m@@ -82,3 +82,27 @@[m [mdef test_history_loads_ratings_without_n_plus_one_queries(client, auth_headers,[m
     assert with_five == with_two[m
     ratings = [r["rating"] for r in client.get("/api/recipes", headers=auth_headers).json()][m
     assert ratings == [4, 4, 4, 3, 3][m
[32m+[m
[32m+[m
[32m+[m[32mdef test_history_sorts_oldest_first(client, auth_headers, monkeypatch):[m
[32m+[m[32m    first, second, third = _seed(client, auth_headers, monkeypatch, [{}, {}, {}])[m
[32m+[m
[32m+[m[32m    newest = client.get("/api/recipes", headers=auth_headers).json()[m
[32m+[m[32m    oldest = client.get("/api/recipes", params={"sort": "oldest"}, headers=auth_headers).json()[m
[32m+[m
[32m+[m[32m    assert [r["id"] for r in newest] == [third, second, first][m
[32m+[m[32m    assert [r["id"] for r in oldest] == [first, second, third][m
[32m+[m
[32m+[m
[32m+[m[32mdef test_remove_rating(client, auth_headers, monkeypatch):[m
[32m+[m[32m    (recipe_id,) = _seed(client, auth_headers, monkeypatch, [{}])[m
[32m+[m[32m    client.post(f"/api/recipes/{recipe_id}/rating", json={"stars": 5}, headers=auth_headers)[m
[32m+[m
[32m+[m[32m    removed = client.delete(f"/api/recipes/{recipe_id}/rating", headers=auth_headers)[m
[32m+[m[32m    assert removed.status_code == 200[m
[32m+[m[32m    assert removed.json()["rating"] is None[m
[32m+[m[32m    assert client.get(f"/api/recipes/{recipe_id}", headers=auth_headers).json()["rating"] is None[m
[32m+[m
[32m+[m[32m    # Quitarla otra vez no falla, y una receta inexistente responde 404.[m
[32m+[m[32m    assert client.delete(f"/api/recipes/{recipe_id}/rating", headers=auth_headers).status_code == 200[m
[32m+[m[32m    assert client.delete("/api/recipes/9999/rating", headers=auth_headers).status_code == 404[m
