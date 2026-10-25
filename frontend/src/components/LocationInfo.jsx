// Extra context about the searched place, from the backend's
// location-info endpoint: a Wikipedia summary, an embedded
// OpenStreetMap map, and a link to YouTube videos of the place.
export default function LocationInfo({ info }) {
  if (!info) return null;
  return (
    <section className="card location-info">
      <h3>About {info.name}</h3>
      {info.wikipedia ? (
        <div className="wiki">
          {info.wikipedia.thumbnail && (
            <img src={info.wikipedia.thumbnail} alt={info.wikipedia.title} />
          )}
          <p>
            {info.wikipedia.extract}{" "}
            <a href={info.wikipedia.url} target="_blank" rel="noreferrer">
              Read more on Wikipedia
            </a>
          </p>
        </div>
      ) : (
        <p>No Wikipedia summary found for this place.</p>
      )}
      <iframe
        title={`Map of ${info.name}`}
        src={info.map_embed_url}
        className="map"
        loading="lazy"
      />
      <p>
        <a href={info.youtube_search_url} target="_blank" rel="noreferrer">
          ▶ Watch videos of {info.name} on YouTube
        </a>
      </p>
    </section>
  );
}
