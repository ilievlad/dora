DELIMITER //
DROP PROCEDURE IF EXISTS update_changes //
CREATE PROCEDURE update_changes() BEGIN
INSERT
  IGNORE INTO dora.changes
SELECT
  source,
  event_type,
  e.commit ->> '$[0].id' AS change_id,
  time_created
FROM
  (
    SELECT
      source,
      event_type,
      JSON_EXTRACT(metadata, '$.commits') AS commit,
      time_created
    FROM
      dora.events_raw
    WHERE
      event_type = "push"
) as e;
END //
DELIMITER ;