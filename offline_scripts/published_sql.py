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
SELECT ReferenceMaster.ReferenceID, RefXrefs.ID AS SiteID, Sites.SiteName, Sites.SiteNumber,
ThumbPath.Path AS ThumbPathName, MediaRenditions.ThumbFileName
FROM ReferenceMaster
JOIN RefXRefs ON ReferenceMaster.ReferenceID=RefXRefs.ReferenceID AND RefXRefs.TableID=189
JOIN Sites ON Sites.SiteID=RefXRefs.ID AND Sites.IsPublic=1
LEFT JOIN MediaXrefs ON Sites.SiteID=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1 AND MediaXrefs.TableID=189
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
LEFT JOIN MediaRenditions ON MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths AS ThumbPath ON MediaRenditions.ThumbPathID=ThumbPath.PathID
WHERE ReferenceMaster.PublicAccess=1
ORDER BY ReferenceMaster.ReferenceID
"""

RELATED_OBJECTS = """
SELECT ReferenceMaster.ReferenceID, RefXrefs.ID AS ObjectID,
ObjTitles.Title, Objects.ObjectNumber, Objects.ClassificationID, Objects.Dated AS ObjectDate,
MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName
FROM ReferenceMaster
JOIN RefXRefs ON ReferenceMaster.ReferenceID=RefXRefs.ReferenceID AND RefXRefs.TableID=108
JOIN Objects ON Objects.ObjectID=RefXRefs.ID AND Objects.PublicAccess=1
JOIN ObjTitles ON Objects.ObjectID=ObjTitles.ObjectID AND ObjTitles.DisplayOrder=1
LEFT JOIN MediaXrefs ON Objects.ObjectID=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
WHERE ReferenceMaster.PublicAccess=1
ORDER BY ReferenceMaster.ReferenceID
"""

RELATED_CONSTITUENTS = """
SELECT ReferenceMaster.ReferenceID, Constituents.ConstituentID,
MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName,
Roles.Role, ConXrefDetails.ConstituentID, Constituents.ConstituentTypeID,
Constituents.DisplayName, Constituents.DisplayDate, Constituents.Remarks, Constituents.AlphaSort
from ReferenceMaster
INNER JOIN ConXrefs ON ReferenceMaster.ReferenceID=ConXrefs.ID AND ConXrefs.TableID=143
INNER JOIN ConXrefDetails ON ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
INNER JOIN Constituents ON ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.PublicAccess=1 AND Constituents.ConstituentTypeID>0
INNER JOIN Roles ON ConXrefs.RoleID=Roles.RoleID
LEFT JOIN MediaXrefs ON Constituents.ConstituentID=MediaXrefs.ID AND MediaXrefs.TableID=23 AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
WHERE ReferenceMaster.PublicAccess=1
ORDER BY ReferenceMaster.ReferenceID
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
