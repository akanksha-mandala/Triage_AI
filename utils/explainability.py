def get_feature_importance(model, feature_names, top_n=3):
    """
    Returns top N important features from trained model.

    Parameters:
        model: trained ML model (RandomForest)
        feature_names: list of feature column names
        top_n: number of top features to return

    Returns:
        List of dictionaries:
        [
            {"feature": str, "importance": float},
            ...
        ]
    """

    if not hasattr(model, "feature_importances_"):
        return []

    importances = model.feature_importances_

    # Pair features with importance scores
    feature_importance_pairs = list(zip(feature_names, importances))

    # Sort descending
    feature_importance_pairs.sort(key=lambda x: x[1], reverse=True)

    # Select top N
    top_features = feature_importance_pairs[:top_n]

    # Format output
    result = [
        {
            "feature": feature,
            "importance": round(score, 4)
        }
        for feature, score in top_features
    ]

    return result