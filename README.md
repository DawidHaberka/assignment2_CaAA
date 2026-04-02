# assignment2_CaAA


## Internet URL:
https://streamlit-frontend-797757706991.europe-west6.run.app/#database-search-results


## Brief explanation of the similarity computation method

To solve the cold start problem and recommend movies to a new user, the following method were used:

**1. Identifying Similar Users:**
Quering the database to find existing users who liked the exact same movies that the current user added to their profile.
Following criteria were used:
* The user must have rated the movie highly, which in our normalized database means `rating_im >= 0.8`;
* Group these users and select the `Top 50` users who have the highest count of overlapping favorite movies.

**2. Generating Predictions:**
Passing these 50 "similar users" into our pre-trained `BigQuery ML Matrix Factorization` model (`ML.RECOMMEND`). The model predicts how these specific users would rate other movies they haven't seen yet. Also filter out niche movies by requiring them to have more than `30` historical ratings.

**3. Match Score Calculation:**
The model returns a raw predicted rating. To present this as a user-friendly `0 - 5` Match Score, we use dynamic normalization:
* Find the highest raw predicted score among the top `10` recommended movies;
* Scale that highest score to a perfect `5.0` (only for one movie);
* The remaining movies are scaled proportionally relative to that top score (e.g., `(raw_score / max_raw_score) * 5.0`), ensuring a realistic and accurate representation of the match.
