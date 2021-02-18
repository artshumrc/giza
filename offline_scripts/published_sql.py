
PUBLISHED = """
SELECT ReferenceMaster.ReferenceID AS ID, ReferenceMaster.Title, ReferenceMaster.Notes,
ReferenceMaster.BoilerText, ReferenceMaster.DisplayDate, ReferenceMaster.YearPublished,
RefFormats.Format, Languages.Language, ReferenceMaster.NumOfPages,
ReferenceMaster.Journal, ReferenceMaster.Series
FROM ReferenceMaster
LEFT JOIN Languages ON ReferenceMaster.LanguageID=Languages.LanguageID
LEFT JOIN RefFormats ON ReferenceMaster.FormatID=RefFormats.FormatID
WHERE ReferenceMaster.PublicAccess=1
ORDER BY ReferenceMaster.ReferenceID
"""

RELATED_SITES = """
SELECT DISTINCT ReferenceMaster.ReferenceID, RefXrefs.ID AS SiteID, Sites.SiteName, Sites.SiteNumber,
ThumbPath.Path AS ThumbPathName, MediaRenditions.ThumbFileName, MediaFiles.ArchIDNum
FROM ReferenceMaster
JOIN RefXRefs ON ReferenceMaster.ReferenceID=RefXRefs.ReferenceID AND RefXRefs.TableID=189
JOIN Sites ON Sites.SiteID=RefXRefs.ID AND Sites.IsPublic=1
LEFT JOIN MediaXrefs ON Sites.SiteID=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1 AND MediaXrefs.TableID=189
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
LEFT JOIN MediaRenditions ON MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths AS ThumbPath ON MediaRenditions.ThumbPathID=ThumbPath.PathID
LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
WHERE ReferenceMaster.PublicAccess=1
AND (
(ThumbPath.Path IS NOT NULL AND MediaRenditions.ThumbFileName IS NOT NULL AND MediaFiles.ArchIDNum IS NOT NULL)
OR (ThumbPath.Path LIKE 'Y:%')
OR (ThumbPath.Path IS NUll AND MediaRenditions.ThumbFileName IS NULL AND MediaFiles.ArchIDNum IS NULL))
ORDER BY ReferenceMaster.ReferenceID, RefXrefs.ID
"""

RELATED_OBJECTS = """
SELECT DISTINCT ReferenceMaster.ReferenceID, RefXrefs.ID AS ObjectID,
replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS Title, Objects.ObjectNumber, Objects.ClassificationID, Objects.Dated AS ObjectDate,
MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName, MediaFiles.ArchIDNum
FROM ReferenceMaster
JOIN RefXRefs ON ReferenceMaster.ReferenceID=RefXRefs.ReferenceID AND RefXRefs.TableID=108
JOIN Objects ON Objects.ObjectID=RefXRefs.ID AND Objects.PublicAccess=1
JOIN ObjTitles ON Objects.ObjectID=ObjTitles.ObjectID AND ObjTitles.DisplayOrder=1
LEFT JOIN MediaXrefs ON Objects.ObjectID=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
WHERE ReferenceMaster.PublicAccess=1
AND (
(MediaPaths.Path IS NOT NULL AND MediaRenditions.ThumbFileName IS NOT NULL AND MediaFiles.ArchIDNum IS NOT NULL)
OR (MediaPaths.Path LIKE 'Y:%')
OR (MediaPaths.Path IS NUll AND MediaRenditions.ThumbFileName IS NULL AND MediaFiles.ArchIDNum IS NULL))
ORDER BY ReferenceMaster.ReferenceID, RefXrefs.ID
"""

RELATED_CONSTITUENTS = """
SELECT DISTINCT ReferenceMaster.ReferenceID,
ConXrefDetails.ConstituentID, Constituents.ConstituentTypeID, Roles.Role,
Constituents.DisplayName, Constituents.DisplayDate, replace(replace(Constituents.Remarks, char(10), ''), char(13), ' ') AS Remarks, Constituents.AlphaSort,
MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName, MediaFiles.ArchIDNum
from ReferenceMaster
INNER JOIN ConXrefs ON ReferenceMaster.ReferenceID=ConXrefs.ID AND ConXrefs.TableID=143
INNER JOIN ConXrefDetails ON ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
INNER JOIN Constituents ON ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.PublicAccess=1 AND Constituents.ConstituentTypeID>0
INNER JOIN Roles ON ConXrefs.RoleID=Roles.RoleID
LEFT JOIN MediaXrefs ON Constituents.ConstituentID=MediaXrefs.ID AND MediaXrefs.TableID=23 AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
WHERE ReferenceMaster.PublicAccess=1
AND (
(MediaPaths.Path IS NOT NULL AND MediaRenditions.ThumbFileName IS NOT NULL AND MediaFiles.ArchIDNum IS NOT NULL)
OR (MediaPaths.Path LIKE 'Y:%')
OR (MediaPaths.Path IS NUll AND MediaRenditions.ThumbFileName IS NULL AND MediaFiles.ArchIDNum IS NULL))
ORDER BY ReferenceMaster.ReferenceID, ConXrefDetails.ConstituentID
"""

RELATED_MEDIA = """
SELECT ReferenceMaster.ReferenceID,
ThumbPath.Path AS ThumbPathName, MediaRenditions.ThumbFileName,
MainPath.Path AS MainPathName, MediaFiles.FileName AS MainFileName
FROM ReferenceMaster
LEFT JOIN MediaXrefs ON ReferenceMaster.ReferenceID=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1 AND MediaXrefs.TableID=143
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
LEFT JOIN MediaRenditions ON MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID=4
LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID AND MediaRenditions.PrimaryFileID=MediaFiles.FileID
LEFT JOIN MediaPaths AS ThumbPath ON MediaRenditions.ThumbPathID=ThumbPath.PathID
LEFT JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
WHERE MediaFiles.FileName IS NOT NULL
AND ReferenceMaster.PublicAccess=1
ORDER BY ReferenceMaster.ReferenceID
"""
