# Site display data
SITES = """
SELECT Sites.SiteID AS ID, SiteName, SiteNumber AS Number, SiteSortNumber, HistoricalNotes,
LegalNotes + ',,' AS BibReferences, LocationNotes,
Sites.Remarks + ',,' AS Remarks,
Sites.Description + ',,' AS Description, Condition,
Environment + ',,' Shafts,
ResearchActivity + ',,' AS ResearchActivity,
ResearcherComments + ',,' AS ResearcherComments, IsPublic,
Active, Sites.harvardID, SiteTypes.SiteTypeID, SiteTypes.SiteType, TextEntries.TextEntry AS ProblemsQuestions
FROM Sites
LEFT OUTER JOIN SiteTypes ON Sites.SiteTypeID=SiteTypes.SiteTypeID AND SiteTypes.SiteTypeID != 0
LEFT JOIN TextEntries ON Sites.SiteID=TextEntries.ID AND TextEntries.TableID=189 AND TextEntries.TextTypeID=1
WHERE IsPublic = 1
ORDER BY Sites.SiteID
"""

SITEDATES = """
SELECT Sites.SiteID, SiteDates.EventType, SiteDates.DateText
FROM Sites
JOIN SiteDates ON Sites.SiteID=SiteDates.SiteID
WHERE Sites.IsPublic=1
ORDER BY Sites.SiteID
"""

# Alternate Numbers for Sites
ALTNUMS = """
SELECT Sites.SiteID, AltNums.AltNum, AltNums.Description
FROM Sites
LEFT JOIN AltNums ON Sites.SiteID=AltNums.ID AND AltNums.TableID=189
WHERE IsPublic = 1
AND AltNum IS NOT NULL
ORDER BY Sites.SiteID
"""

# Related Objects for all Sites
RELATED_OBJECTS = """
SELECT Sites.SiteID, SiteObjXrefs.ObjectID,
replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS Title, Objects.ObjectNumber, Objects.ClassificationID, Objects.Dated AS ObjectDate,
MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName
FROM Sites
JOIN SiteObjXrefs ON Sites.SiteID=SiteObjXrefs.SiteID
JOIN Objects ON SiteObjXrefs.ObjectID=Objects.ObjectID AND Objects.PublicAccess=1
LEFT JOIN ObjTitles ON SiteObjXrefs.ObjectID=ObjTitles.ObjectID AND ObjTitles.DisplayOrder=1
LEFT JOIN MediaXrefs ON Objects.ObjectID=MediaXrefs.ID AND MediaXrefs.TableID=108 AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
WHERE Sites.IsPublic = 1
ORDER BY Sites.SiteID
"""

# Related Constituents for all Sites
# Also grab the primary thumbnail photo for each Constituent
RELATED_CONSTITUENTS = """
SELECT ConXrefs.ID AS SiteID, Roles.Role, ConXrefDetails.ConstituentID, Constituents.ConstituentTypeID,
Constituents.DisplayName, Constituents.DisplayDate, replace(replace(Constituents.Remarks, char(10), ''), char(13), ' ') AS Remarks,
MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName
FROM ConXrefs
INNER JOIN ConXrefDetails ON ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
INNER JOIN Constituents ON ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.PublicAccess=1
INNER JOIN Roles ON ConXrefs.RoleID=Roles.RoleID
INNER JOIN Sites ON ConXrefs.ID=Sites.SiteID AND Sites.IsPublic=1
LEFT JOIN MediaXrefs ON Constituents.ConstituentID=MediaXrefs.ID AND MediaXrefs.TableID=23 AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
WHERE ConXrefs.TableID=189
ORDER BY ConXrefs.ID
"""

# Related Published Documents for all Sites
RELATED_PUBLISHED = """
SELECT RefXrefs.ID AS SiteID, ReferenceMaster.ReferenceID, ReferenceMaster.Title,
ReferenceMaster.BoilerText, ReferenceMaster.DisplayDate,
ThumbPath.Path AS ThumbPathName, MediaRenditions.ThumbFileName,
MainPath.Path AS MainPathName, MediaFiles.FileName AS MainFileName
FROM Sites
JOIN RefXRefs ON Sites.SiteID=RefXRefs.ID
JOIN ReferenceMaster ON RefXRefs.ReferenceID=ReferenceMaster.ReferenceID AND ReferenceMaster.PublicAccess=1
LEFT JOIN MediaXrefs ON ReferenceMaster.ReferenceID=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1 AND MediaXrefs.TableID=143
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
LEFT JOIN MediaRenditions ON MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
LEFT JOIN MediaPaths AS ThumbPath ON MediaRenditions.ThumbPathID=ThumbPath.PathID
LEFT JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
WHERE MediaRenditions.PrimaryFileID=MediaFiles.FileID
AND MediaTypeID=4
AND Sites.IsPublic=1
ORDER BY SiteID
"""

# Related Media for all Sites
RELATED_MEDIA = """
SELECT MediaXrefs.ID AS SiteID, MediaMaster.MediaMasterID, MediaXrefs.PrimaryDisplay,
MediaRenditions.MediaTypeID, MediaRenditions.RenditionNumber, replace(replace(MediaMaster.Description, char(10), ''), char(13), ' ') AS Description,
MediaMaster.MediaView, MediaMaster.PublicCaption,
ThumbPath.Path AS ThumbPathName, MediaRenditions.ThumbFileName,
MainPath.Path AS MainPathName, MediaFiles.FileName AS MainFileName
FROM MediaXrefs
INNER JOIN Sites ON MediaXrefs.ID=Sites.SiteID AND Sites.IsPublic=1
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
LEFT JOIN MediaPaths AS ThumbPath ON MediaRenditions.ThumbPathID=ThumbPath.PathID
LEFT JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
WHERE MediaXrefs.TableID=189
AND MediaRenditions.PrimaryFileID=MediaFiles.FileID
ORDER BY MediaXrefs.ID
"""
