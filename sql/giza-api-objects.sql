/* Object display data 
TODO: Get Primary Image URL (need an image server first) */
/* Need Department? */
SELECT Objects.ObjectID, Objects.ObjectNumber, Objects.ObjectStatusID, Objects.ClassificationID, Objects.ObjectName + ',,' as ObjectOwnerDetails,
Objects.Dated as EntryDate, replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS Title, Objects.Medium + ',,' as Medium, 
Objects.Dimensions + ',,' as Dimensions, Objects.CreditLine, Objects.Description + ',,' AS Description, Objects.Provenance, 
Objects.PubReferences + ',,' AS PubReferences
FROM Objects 
LEFT JOIN ObjTitles on Objects.ObjectID=ObjTitles.ObjectID
WHERE Objects.PublicAccess = 1
AND Objects.ObjectID >= 0
ORDER BY Objects.ObjectID

