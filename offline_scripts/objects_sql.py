# Object display data
OBJECTS = """
SELECT Objects.ObjectID as ID, Objects.ObjectNumber as Number, Objects.ObjectStatusID, Objects.ClassificationID,
(Classifications.Classification + ISNULL(('-' + Classifications.SubClassification),'')) AS ClassificationText,
Objects.ObjectName + ',,' as ObjectOwnerDetails, Departments.Department, ObjContext.Period,
Objects.Dated as EntryDate, replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS Title, Objects.Medium + ',,' as Medium,
Objects.Dimensions + ',,' as Dimensions, Objects.CreditLine, Objects.Description + ',,' AS Description, Objects.Provenance,
Objects.PubReferences + ',,' AS BibReferences, Objects.Notes + ',,' AS Notes, Objects.Chat + ',,' as DiaryTranscription,
Objects.CuratorialRemarks + ',,' AS Remarks, TextEntries.TextEntry as ProblemsQuestions
FROM Objects
LEFT JOIN ObjTitles on Objects.ObjectID=ObjTitles.ObjectID AND ObjTitles.DisplayOrder=1
LEFT JOIN Classifications on Objects.ClassificationID=Classifications.ClassificationID
LEFT JOIN Departments on Objects.DepartmentID=Departments.DepartmentID
LEFT JOIN ObjContext on Objects.ObjectID=ObjContext.ObjectID
LEFT JOIN TextEntries on Objects.ObjectID=TextEntries.ID AND TextEntries.TableID=108 AND TextEntries.TextTypeID=12
WHERE Objects.PublicAccess = 1
AND Objects.ObjectID >= 0
ORDER BY Objects.ObjectID
"""

GEOCODES = """
SELECT ObjGeography.ObjectID as ID, ObjGeography.GeoCodeID, GeoCodes.GeoCode, ObjGeography.Region, ObjGeography.City, Objects.ClassificationID
FROM ObjGeography
JOIN GeoCodes on ObjGeography.GeoCodeID=GeoCodes.GeoCodeID
JOIN Objects on ObjGeography.ObjectID=Objects.ObjectID AND Objects.PublicAccess=1
WHERE ObjGeography.ObjectID >= 0
AND ObjGeography.GeoCodeID > 0
"""

# Alternate Numbers for Objects
ALTNUMS = """
SELECT Objects.ObjectID, Objects.ClassificationID, AltNums.AltNum, AltNums.Description
FROM Objects
LEFT JOIN AltNums ON Objects.ObjectID=AltNums.ID AND AltNums.TableID=108
WHERE Objects.PublicAccess = 1
AND AltNums.AltNum IS NOT NULL
AND AltNums.Description != 'Artemis_ObjectID'
ORDER BY Objects.ObjectID
"""

# Flex Fields (i.e. user defined fields) for Objects with Classification `Human Remains`
FLEXFIELDS = """
SELECT Objects.ObjectID, Objects.ClassificationID, UserFieldGroups.GroupName, UserFields.UserFieldName,
UserFieldValueAuthority.UserFieldValue
FROM UserFieldXrefs
JOIN UserFields on UserFieldXrefs.UserFieldID=UserFields.UserFieldID
JOIN UserFieldValueAuthority on UserFields.UserFieldID=UserFieldValueAuthority.UserFieldID AND UserFieldValueAuthority.UserFieldValue != '(not assigned)'
JOIN UserFieldGroups on UserFieldXrefs.UserFieldGroupID=UserFieldGroups.UserFieldGroupID
JOIN Objects on UserFieldXrefs.ID=Objects.ObjectID AND Objects.ClassificationID=83
ORDER BY Objects.ObjectID
"""

# Related Sites for all Objects
RELATED_SITES = """
SELECT Objects.ObjectID as ID, SiteObjXrefs.SiteID,
Sites.SiteName, Sites.SiteNumber, Objects.ClassificationID,
MediaPaths.Path as ThumbPathName, MediaRenditions.ThumbFileName
FROM Objects
JOIN SiteObjXrefs ON Objects.ObjectID=SiteObjXrefs.ObjectID
JOIN Sites ON SiteObjXrefs.SiteID=Sites.SiteID AND Sites.IsPublic = 1
LEFT JOIN MediaXrefs on Sites.SiteID=MediaXrefs.ID AND MediaXrefs.TableID=189 AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
LEFT JOIN MediaRenditions on MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths on MediaRenditions.ThumbPathID=MediaPaths.PathID
WHERE Objects.PublicAccess = 1
ORDER BY Objects.ObjectID
"""

# Related Constituents (Modern and Ancient) for all Objects
RELATED_CONSTITUENTS = """
SELECT ConXrefs.ID as ID, Roles.Role, Roles.RoleID, ConXrefDetails.ConstituentID, Constituents.ConstituentTypeID,
Constituents.DisplayName, Constituents.DisplayDate, Objects.ClassificationID, Constituents.Remarks,
MediaPaths.Path as ThumbPathName, MediaRenditions.ThumbFileName
FROM ConXrefs
INNER JOIN ConXrefDetails on ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
INNER JOIN Constituents on ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.Active=1
INNER JOIN Roles on ConXrefs.RoleID=Roles.RoleID
INNER JOIN Objects on ConXrefs.ID=Objects.ObjectID AND Objects.PublicAccess=1
LEFT JOIN MediaXrefs on Constituents.ConstituentID=MediaXrefs.ID AND MediaXrefs.TableID=23 AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
LEFT JOIN MediaRenditions on MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths on MediaRenditions.ThumbPathID=MediaPaths.PathID
WHERE ConXrefs.TableID=108
ORDER BY ConXrefs.ID
"""

# Related Published Documents for all Objects
RELATED_PUBLISHED = """
SELECT RefXrefs.ID as ID, ReferenceMaster.ReferenceID, ReferenceMaster.Title, ReferenceMaster.BoilerText,
Objects.ClassificationID, ReferenceMaster.DisplayDate,
MainPath.Path as MainPathName, MediaFiles.FileName as MainFileName
FROM Objects
JOIN RefXRefs on Objects.ObjectID=RefXRefs.ID
JOIN ReferenceMaster on RefXrefs.ReferenceID=ReferenceMaster.ReferenceID
JOIN MediaXrefs on ReferenceMaster.ReferenceID=MediaXrefs.ID AND MediaXrefs.TableID=143 AND MediaXrefs.PrimaryDisplay=1
JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
JOIN MediaRenditions on MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID
JOIN MediaFiles on MediaRenditions.RenditionID=MediaFiles.RenditionID
JOIN MediaPaths AS MainPath on MediaFiles.PathID=MainPath.PathID
WHERE MediaRenditions.PrimaryFileID=MediaFiles.FileID
AND MediaTypeID=4
AND Objects.PublicAccess=1
ORDER BY Objects.ObjectID
"""

RELATED_UNPUBLISHED = """
SELECT Associations.ID1 as ID, Associations.ID2 as UnpublishedID, Objects.ObjectNumber,
replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS UnpublishedTitle, Objects.ClassificationID, Objects.Dated as ObjectDate,
MediaPaths.Path as ThumbPathName, MediaRenditions.ThumbFileName
FROM Associations
LEFT JOIN ObjTitles on Associations.ID2=ObjTitles.ObjectID
LEFT JOIN Objects on Associations.ID1=Objects.ObjectID AND Objects.PublicAccess=1
LEFT JOIN MediaXrefs on Associations.ID2=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
LEFT JOIN MediaRenditions on MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths on MediaRenditions.ThumbPathID=MediaPaths.PathID
WHERE Associations.TableID=108
AND RelationshipID=6
ORDER BY ID1
"""

# Related Media for all Objects
RELATED_MEDIA = """
SELECT MediaXrefs.ID as ID, MediaMaster.MediaMasterID, Objects.ClassificationID, MediaXrefs.PrimaryDisplay,
MediaRenditions.MediaTypeID, MediaMaster.Description, MediaMaster.PublicCaption,
ThumbPath.Path as ThumbPathName, MediaRenditions.ThumbFileName,
MainPath.Path as MainPathName, MediaFiles.FileName as MainFileName
FROM MediaXrefs
LEFT JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
LEFT JOIN MediaRenditions on MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
JOIN Objects on MediaXrefs.ID=Objects.ObjectID AND Objects.PublicAccess=1
LEFT JOIN MediaFiles on MediaRenditions.RenditionID=MediaFiles.RenditionID
LEFT JOIN MediaPaths AS ThumbPath on MediaRenditions.ThumbPathID=ThumbPath.PathID
LEFT JOIN MediaPaths AS MainPath on MediaFiles.PathID=MainPath.PathID
WHERE MediaXrefs.TableID=108
AND MediaRenditions.PrimaryFileID=MediaFiles.FileID
ORDER BY MediaXrefs.ID
"""
