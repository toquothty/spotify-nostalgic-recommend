# Fix for the generate endpoint - replace the existing generate function


@router.get("/generate")
async def generate_recommendations(
    session_id: str,
    recommendation_type: str = "cluster",
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Generate new recommendations for user"""
    session = get_current_session(session_id, db)
    user = db.query(User).filter(User.id == session.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check rate limiting
    if not can_generate_recommendations(session, db):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before generating new recommendations.",
        )

    try:
        # Check if user has analyzed tracks
        track_count = db.query(Track).filter(Track.user_id == user.id).count()
        if track_count == 0:
            raise HTTPException(
                status_code=400, detail="Please analyze your library first"
            )

        # Generate recommendations based on type
        if recommendation_type == "cluster":
            recommendations = recommendation_engine.generate_cluster_recommendations(
                session.access_token, user.id, limit, db
            )
        elif recommendation_type == "nostalgia":
            if not user.date_of_birth:
                raise HTTPException(
                    status_code=400,
                    detail="Date of birth required for nostalgia recommendations",
                )
            recommendations = recommendation_engine.generate_nostalgia_recommendations(
                session.access_token, user.id, limit, db
            )
        elif recommendation_type == "forgotten":
            recommendations = recommendation_engine.get_forgotten_favorites(
                session.access_token, user.id, limit, db
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid recommendation type")

        # Update rate limiting only if we got recommendations
        if recommendations:
            update_recommendation_limits(session, db)

        # Get the stored recommendations from database instead of returning raw Spotify data
        stored_recommendations = (
            db.query(Recommendation)
            .filter(
                Recommendation.user_id == user.id,
                Recommendation.recommendation_type == recommendation_type,
            )
            .order_by(Recommendation.created_at.desc())
            .limit(limit)
            .all()
        )

        # Convert to the format expected by frontend
        formatted_recommendations = []
        for rec in stored_recommendations:
            formatted_rec = {
                "id": rec.id,
                "spotify_track_id": rec.spotify_track_id,
                "track_name": rec.track_name,
                "artist_name": rec.artist_name,
                "album_name": rec.album_name,
                "preview_url": rec.preview_url,
                "external_url": rec.external_url,
                "image_url": rec.image_url,
                "recommendation_type": rec.recommendation_type,
                "confidence_score": rec.score,
                "source_cluster_id": rec.source_cluster_id,
                "created_at": rec.created_at.isoformat(),
                "user_liked": rec.user_liked,
                "user_already_knew": rec.user_already_knew,
            }
            formatted_recommendations.append(formatted_rec)

        return {
            "recommendations": formatted_recommendations,
            "count": len(formatted_recommendations),
            "type": recommendation_type,
        }

    except Exception as e:
        logger.error(f"Failed to generate recommendations: {e}")
        raise HTTPException(
            status_code=500, detail=f"Recommendation generation failed: {str(e)}"
        )
