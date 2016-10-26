PUBLISHED = """
SELECT ReferenceMaster.ReferenceID as ID, ReferenceMaster.Title,
ReferenceMaster.BoilerText, ReferenceMaster.DisplayDate, ReferenceMaster.YearPublished,
RefFormats.Format, Languages.Language, ReferenceMaster.NumOfPages,
ReferenceMaster.Journal, ReferenceMaster.Series
FROM ReferenceMaster
LEFT JOIN Languages on ReferenceMaster.LanguageID=Languages.LanguageID
LEFT JOIN RefFormats on ReferenceMaster.FormatID=RefFormats.FormatID
ORDER BY ReferenceMaster.ReferenceID
"""

RELATED_SITES = """
SELECT ReferenceMaster.ReferenceID, RefXrefs.ID as SiteID, Sites.SiteName, Sites.SiteNumber,
ThumbPath.Path as ThumbPathName, MediaRenditions.ThumbFileName
FROM ReferenceMaster
JOIN RefXRefs on ReferenceMaster.ReferenceID=RefXRefs.ReferenceID AND RefXRefs.TableID=189
JOIN Sites on Sites.SiteID=RefXRefs.ID AND Sites.IsPublic=1
LEFT JOIN MediaXrefs on Sites.SiteID=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1 AND MediaXrefs.TableID=189
LEFT JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
LEFT JOIN MediaRenditions on MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths AS ThumbPath on MediaRenditions.ThumbPathID=ThumbPath.PathID
ORDER BY ReferenceMaster.ReferenceID
"""

RELATED_OBJECTS = """
SELECT ReferenceMaster.ReferenceID, RefXrefs.ID as ObjectID,
ObjTitles.Title, Objects.ObjectNumber, Objects.ClassificationID, Objects.Dated as ObjectDate,
MediaPaths.Path as ThumbPathName, MediaRenditions.ThumbFileName
FROM ReferenceMaster
JOIN RefXRefs on ReferenceMaster.ReferenceID=RefXRefs.ReferenceID AND RefXRefs.TableID=108
JOIN Objects on Objects.ObjectID=RefXRefs.ID AND Objects.PublicAccess=1
JOIN ObjTitles ON Objects.ObjectID=ObjTitles.ObjectID
LEFT JOIN MediaXrefs on Objects.ObjectID=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
LEFT JOIN MediaRenditions on MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths on MediaRenditions.ThumbPathID=MediaPaths.PathID
ORDER BY ReferenceMaster.ReferenceID
"""

RELATED_CONSTITUENTS = """
SELECT ReferenceMaster.ReferenceID, Constituents.ConstituentID,
MediaPaths.Path as ThumbPathName, MediaRenditions.ThumbFileName,
Roles.Role, ConXrefDetails.ConstituentID, Constituents.ConstituentTypeID,
Constituents.DisplayName, Constituents.DisplayDate, Constituents.Remarks, Constituents.AlphaSort
from ReferenceMaster
INNER JOIN ConXrefs on ReferenceMaster.ReferenceID=ConXrefs.ID AND ConXrefs.TableID=143
INNER JOIN ConXrefDetails on ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
INNER JOIN Constituents on ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.PublicAccess=1 AND Constituents.ConstituentTypeID>0
INNER JOIN Roles on ConXrefs.RoleID=Roles.RoleID
LEFT JOIN MediaXrefs on Constituents.ConstituentID=MediaXrefs.ID AND MediaXrefs.TableID=23 AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
LEFT JOIN MediaRenditions on MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths on MediaRenditions.ThumbPathID=MediaPaths.PathID
ORDER BY ReferenceMaster.ReferenceID
"""

RELATED_MEDIA = """
SELECT ReferenceMaster.ReferenceID,
ThumbPath.Path as ThumbPathName, MediaRenditions.ThumbFileName,
MainPath.Path as MainPathName, MediaFiles.FileName as MainFileName
FROM ReferenceMaster
LEFT JOIN MediaXrefs on ReferenceMaster.ReferenceID=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1 AND MediaXrefs.TableID=143
LEFT JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
LEFT JOIN MediaRenditions on MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID=4
LEFT JOIN MediaFiles on MediaRenditions.RenditionID=MediaFiles.RenditionID AND MediaRenditions.PrimaryFileID=MediaFiles.FileID
LEFT JOIN MediaPaths AS ThumbPath on MediaRenditions.ThumbPathID=ThumbPath.PathID
LEFT JOIN MediaPaths AS MainPath on MediaFiles.PathID=MainPath.PathID
WHERE MediaFiles.FileName IS NOT NULL
ORDER BY ReferenceMaster.ReferenceID
"""
