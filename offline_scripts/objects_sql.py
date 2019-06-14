from __future__ import unicode_literals
# Object display data
OBJECTS = """
SELECT Objects.ObjectID AS ID, Objects.ObjectNumber AS Number, Objects.ObjectStatusID, Objects.ClassificationID,
(Classifications.Classification + ISNULL(('-' + Classifications.SubClassification),'')) AS ClassificationText,
Objects.ObjectName + ',,' AS ObjectOwnerDetails, Departments.Department, ObjContext.Period,
Objects.Dated AS EntryDate, replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS Title, Objects.Medium + ',,' AS Medium,
Objects.Dimensions + ',,' AS Dimensions, Objects.CreditLine, Objects.Description + ',,' AS Description, Objects.Provenance,
Objects.PubReferences + ',,' AS BibReferences, Objects.Notes + ',,' AS Notes, Objects.Chat + ',,' AS DiaryTranscription,
Objects.CuratorialRemarks + ',,' AS Remarks, TextEntries.TextEntry AS ProblemsQuestions
FROM Objects
LEFT JOIN ObjTitles ON Objects.ObjectID=ObjTitles.ObjectID AND ObjTitles.DisplayOrder=1
LEFT JOIN Classifications ON Objects.ClassificationID=Classifications.ClassificationID
LEFT JOIN Departments ON Objects.DepartmentID=Departments.DepartmentID
LEFT JOIN ObjContext ON Objects.ObjectID=ObjContext.ObjectID
LEFT JOIN TextEntries ON Objects.ObjectID=TextEntries.ID AND TextEntries.TableID=108 AND TextEntries.TextTypeID=12
WHERE Objects.PublicAccess = 1
AND Objects.ObjectID >= 0
ORDER BY Objects.ObjectID
"""

GEOCODES = """
SELECT ObjGeography.ObjectID AS ID, ObjGeography.GeoCodeID, GeoCodes.GeoCode, ObjGeography.Region, ObjGeography.City, Objects.ClassificationID
FROM ObjGeography
JOIN GeoCodes ON ObjGeography.GeoCodeID=GeoCodes.GeoCodeID
JOIN Objects ON ObjGeography.ObjectID=Objects.ObjectID AND Objects.PublicAccess=1
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
UserFieldXrefs.FieldValue
FROM UserFieldXrefs
JOIN UserFields ON UserFieldXrefs.UserFieldID=UserFields.UserFieldID
JOIN UserFieldGroups ON UserFieldXrefs.UserFieldGroupID=UserFieldGroups.UserFieldGroupID
JOIN Objects ON UserFieldXrefs.ID=Objects.ObjectID AND Objects.ClassificationID=83
WHERE UserFieldXrefs.FieldValue != '(not assigned)'
ORDER BY Objects.ObjectID
"""

# Related Sites for all Objects
RELATED_SITES = """
SELECT Objects.ObjectID AS ID, SiteObjXrefs.SiteID,
Sites.SiteName, Sites.SiteNumber, Objects.ClassificationID,
MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName
FROM Objects
JOIN SiteObjXrefs ON Objects.ObjectID=SiteObjXrefs.ObjectID
JOIN Sites ON SiteObjXrefs.SiteID=Sites.SiteID AND Sites.IsPublic = 1
LEFT JOIN MediaXrefs ON Sites.SiteID=MediaXrefs.ID AND MediaXrefs.TableID=189 AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
WHERE Objects.PublicAccess = 1
ORDER BY Objects.ObjectID
"""

# Related Constituents (Modern and Ancient) for all Objects
RELATED_CONSTITUENTS = """
SELECT ConXrefs.ID AS ID, Roles.Role, Roles.RoleID, ConXrefDetails.ConstituentID, Constituents.ConstituentTypeID,
Constituents.DisplayName, Constituents.DisplayDate, Objects.ClassificationID, replace(replace(Constituents.Remarks, char(10), ''), char(13), ' ') AS Remarks,
MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName
FROM ConXrefs
INNER JOIN ConXrefDetails ON ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
INNER JOIN Constituents ON ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.Active=1
INNER JOIN Roles ON ConXrefs.RoleID=Roles.RoleID
INNER JOIN Objects ON ConXrefs.ID=Objects.ObjectID AND Objects.PublicAccess=1
LEFT JOIN MediaXrefs ON Constituents.ConstituentID=MediaXrefs.ID AND MediaXrefs.TableID=23 AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
WHERE ConXrefs.TableID=108
ORDER BY ConXrefs.ID
"""

# Related Published Documents for all Objects
RELATED_PUBLISHED = """
SELECT RefXrefs.ID AS ID, ReferenceMaster.ReferenceID, ReferenceMaster.Title, ReferenceMaster.BoilerText,
Objects.ClassificationID, ReferenceMaster.DisplayDate,
MainPath.Path AS MainPathName, MediaFiles.FileName AS MainFileName
FROM Objects
JOIN RefXRefs ON Objects.ObjectID=RefXRefs.ID
JOIN ReferenceMaster ON RefXrefs.ReferenceID=ReferenceMaster.ReferenceID AND ReferenceMaster.PublicAccess=1
JOIN MediaXrefs ON ReferenceMaster.ReferenceID=MediaXrefs.ID AND MediaXrefs.TableID=143 AND MediaXrefs.PrimaryDisplay=1
JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
JOIN MediaRenditions ON MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID
JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
WHERE MediaRenditions.PrimaryFileID=MediaFiles.FileID
AND MediaTypeID=4
AND Objects.PublicAccess=1
ORDER BY Objects.ObjectID
"""

RELATED_UNPUBLISHED = """
SELECT Associations.ID1 AS ID, Associations.ID2 AS UnpublishedID, Objects.ObjectNumber,
replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS UnpublishedTitle, Objects.ClassificationID, Objects.Dated AS ObjectDate,
MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName
FROM Associations
LEFT JOIN ObjTitles ON Associations.ID2=ObjTitles.ObjectID
LEFT JOIN Objects ON Associations.ID1=Objects.ObjectID AND Objects.PublicAccess=1
LEFT JOIN MediaXrefs ON Associations.ID2=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
WHERE Associations.TableID=108
AND RelationshipID=6
ORDER BY ID1
"""

# Related Media for all Objects
RELATED_MEDIA = """
SELECT MediaXrefs.ID AS ID, MediaMaster.MediaMasterID, Objects.ClassificationID, MediaXrefs.PrimaryDisplay,
MediaRenditions.MediaTypeID, MediaRenditions.RenditionNumber, replace(replace(MediaMaster.Description, char(10), ''), char(13), ' ') AS Description,
MediaMaster.MediaView, replace(replace(MediaMaster.PublicCaption, char(10), ''), char(13), ' ') AS PublicCaption,
ThumbPath.Path AS ThumbPathName, MediaRenditions.ThumbFileName,
MainPath.Path AS MainPathName, MediaFiles.FileName AS MainFileName
FROM MediaXrefs
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
JOIN Objects ON MediaXrefs.ID=Objects.ObjectID AND Objects.PublicAccess=1
LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
LEFT JOIN MediaPaths AS ThumbPath ON MediaRenditions.ThumbPathID=ThumbPath.PathID
LEFT JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
WHERE MediaXrefs.TableID=108
AND MediaRenditions.PrimaryFileID=MediaFiles.FileID
ORDER BY MediaXrefs.ID
"""
