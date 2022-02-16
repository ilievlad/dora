
DELIMITER //
DROP PROCEDURE IF EXISTS update_deployments //
CREATE PROCEDURE update_deployments() BEGIN
INSERT
  IGNORE INTO dora.deployments
SELECT
id as deploy_id,
metadata ->> '$.commitId' AS change_id,
TIMESTAMP(metadata ->> '$.buildTimestamp') AS time_created,
metadata ->> '$.projectName' AS project_name
FROM
  dora.events_raw
WHERE
  event_type = "deployment"
  and metadata ->> '$.buildStatus' = 'SUCCESS';
END //
DELIMITER ;