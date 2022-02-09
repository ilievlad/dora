DELIMITER //
CREATE PROCEDURE update_incidents() BEGIN
INSERT
  IGNORE INTO dora.incidents
  SELECT
    source,
    incident_id,
    MIN(
      IF(
        root.time_created < incident.time_created,
        root.time_created,
        incident.time_created
      )
    ) as time_created,
    MAX(time_resolved) as time_resolved,
    root_cause as changes
  FROM
    (
      SELECT
        source,
        id as incident_id,
        time_created,
        TIMESTAMP(metadata ->> '$.issue.closed_on') AS time_resolved,
        metadata ->> '$.root_cause' as root_cause
      FROM
        events_raw
      WHERE
        event_type = 'incident'
    ) incident
    LEFT JOIN (
      SELECT
        time_created,
        change_id
      FROM
        deployments
    ) root on root.change_id = root_cause
    GROUP BY 1, 2
  ON DUPLICATE KEY UPDATE
    time_created = VALUES(time_created),
    time_resolved = VALUES(time_resolved),
    changes = VALUES(changes);
END //
DELIMITER ;
