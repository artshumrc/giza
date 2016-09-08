# Site display data
# TODO: Get Primary Image URL (need an image server first)
SITES = """
SELECT Sites.SiteID as ID, SiteName, SiteNumber as Number, SiteSortNumber, HistoricalNotes,
LegalNotes + ',,' AS BibReferences, LocationNotes,
Sites.Remarks + ',,' AS Remarks,
Sites.Description + ',,' AS Description, Condition,
Environment + ',,' Shafts,
ResearchActivity + ',,' AS ResearchActivity,
ResearcherComments + ',,' AS ResearcherComments, IsPublic,
Active, Sites.harvardID, SiteTypes.SiteTypeID, SiteTypes.SiteType,
(ISNULL(SiteDates.EventType,'') + '_' + ISNULL(SiteDates.DateText,'')) AS SiteDates_EventType_DateText
FROM Sites
LEFT OUTER JOIN SiteTypes ON Sites.SiteTypeID=SiteTypes.SiteTypeID AND SiteTypes.SiteTypeID != 0
LEFT OUTER JOIN SiteDates ON Sites.SiteID=SiteDates.SiteID
WHERE IsPublic = 1
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
# TODO: Get Primary Image URL (need an image server first)
RELATED_OBJECTS = """
SELECT Sites.SiteID, SiteObjXrefs.ObjectID,
replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS Title, Objects.ObjectNumber, Objects.ClassificationID, Objects.Dated as ObjectDate,
MediaPaths.Path as ThumbPathName, MediaRenditions.ThumbFileName
FROM Sites
LEFT JOIN SiteObjXrefs ON Sites.SiteID=SiteObjXrefs.SiteID
LEFT JOIN Objects ON SiteObjXrefs.ObjectID=Objects.ObjectID
LEFT JOIN ObjTitles ON SiteObjXrefs.ObjectID=ObjTitles.ObjectID
LEFT JOIN MediaXrefs on Objects.ObjectID=MediaXrefs.ID
LEFT JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
LEFT JOIN MediaRenditions on MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths on MediaRenditions.ThumbPathID=MediaPaths.PathID
WHERE Sites.IsPublic = 1
AND Objects.PublicAccess = 1
AND MediaXrefs.TableID=108
AND MediaXrefs.PrimaryDisplay=1
ORDER BY Sites.SiteID
"""

# Related Constituents (Modern and Ancient) for all Sites
# Also grab the primary thumbnail photo for each Constituent
RELATED_CONSTITUENTS = """
SELECT ConXrefs.ID as SiteID, Roles.Role, ConXrefDetails.ConstituentID, Constituents.ConstituentTypeID,
Constituents.DisplayName, Constituents.DisplayDate, Constituents.Remarks,
MediaPaths.Path as ThumbPathName, MediaRenditions.ThumbFileName
FROM ConXrefs
LEFT JOIN ConXrefDetails on ConXrefs.ConXrefID=ConXrefDetails.ConXrefID
LEFT JOIN Constituents on ConXrefDetails.ConstituentID=Constituents.ConstituentID
LEFT JOIN Roles on ConXrefs.RoleID=Roles.RoleID
LEFT JOIN MediaXrefs on Constituents.ConstituentID=MediaXrefs.ID
LEFT JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
LEFT JOIN MediaRenditions on MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths on MediaRenditions.ThumbPathID=MediaPaths.PathID
WHERE ConXrefs.TableID=189
AND Constituents.Active=1
AND ConXrefDetails.Unmasked=1
AND MediaXrefs.TableID=23
AND MediaXrefs.PrimaryDisplay=1
ORDER BY ConXrefs.ID
"""

# Related Published Documents for all Sites
RELATED_PUBLISHED = """
SELECT RefXrefs.ID as SiteID, ReferenceMaster.ReferenceID, ReferenceMaster.BoilerText, ReferenceMaster.DisplayDate
FROM RefXrefs
LEFT JOIN ReferenceMaster on RefXrefs.ReferenceID=ReferenceMaster.ReferenceID
WHERE RefXrefs.TableID=189
ORDER BY RefXrefs.ID
"""

# Related Media for all Sites
RELATED_MEDIA = """
SELECT MediaXrefs.ID as SiteID, MediaMaster.MediaMasterID, MediaXrefs.PrimaryDisplay, MediaRenditions.RenditionNumber,
ThumbPath.Path as ThumbPathName, MediaRenditions.ThumbFileName,
MainPath.Path as MainPathName, MediaFiles.FileName as MainFileName
FROM MediaXrefs
LEFT JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
LEFT JOIN MediaRenditions on MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaFiles on MediaRenditions.RenditionID=MediaFiles.RenditionID
LEFT JOIN MediaPaths AS ThumbPath on MediaRenditions.ThumbPathID=ThumbPath.PathID
LEFT JOIN MediaPaths AS MainPath on MediaFiles.PathID=MainPath.PathID
WHERE MediaXrefs.TableID=189
AND MediaMaster.PublicAccess=1
AND MediaRenditions.MediaTypeID=1
AND MediaRenditions.PrimaryFileID=MediaFiles.FileID
ORDER BY MediaXrefs.ID
"""
