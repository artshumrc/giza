# Site display data
SITES = """
SELECT Sites.SiteID as ID, SiteName, SiteNumber as Number, SiteSortNumber, HistoricalNotes,
LegalNotes + ',,' AS BibReferences, LocationNotes,
Sites.Remarks + ',,' AS Remarks,
Sites.Description + ',,' AS Description, Condition,
Environment + ',,' Shafts,
ResearchActivity + ',,' AS ResearchActivity,
ResearcherComments + ',,' AS ResearcherComments, IsPublic,
Active, Sites.harvardID, SiteTypes.SiteTypeID, SiteTypes.SiteType, TextEntries.TextEntry as ProblemsQuestions
FROM Sites
LEFT OUTER JOIN SiteTypes ON Sites.SiteTypeID=SiteTypes.SiteTypeID AND SiteTypes.SiteTypeID != 0
LEFT JOIN TextEntries on Sites.SiteID=TextEntries.ID AND TextEntries.TableID=189 AND TextEntries.TextTypeID=1
WHERE IsPublic = 1
ORDER BY Sites.SiteID
"""

SITEDATES = """
SELECT Sites.SiteID, SiteDates.EventType, SiteDates.DateText
FROM Sites
JOIN SiteDates on Sites.SiteID=SiteDates.SiteID
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
replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS Title, Objects.ObjectNumber, Objects.ClassificationID, Objects.Dated as ObjectDate,
MediaPaths.Path as ThumbPathName, MediaRenditions.ThumbFileName
FROM Sites
LEFT JOIN SiteObjXrefs ON Sites.SiteID=SiteObjXrefs.SiteID
LEFT JOIN Objects ON SiteObjXrefs.ObjectID=Objects.ObjectID
LEFT JOIN ObjTitles ON SiteObjXrefs.ObjectID=ObjTitles.ObjectID
LEFT JOIN MediaXrefs on Objects.ObjectID=MediaXrefs.ID AND MediaXrefs.TableID=108 AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
LEFT JOIN MediaRenditions on MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths on MediaRenditions.ThumbPathID=MediaPaths.PathID
WHERE Sites.IsPublic = 1
AND Objects.PublicAccess = 1
ORDER BY Sites.SiteID
"""

# Related Constituents for all Sites
# Also grab the primary thumbnail photo for each Constituent
RELATED_CONSTITUENTS = """
SELECT ConXrefs.ID as SiteID, Roles.Role, ConXrefDetails.ConstituentID, Constituents.ConstituentTypeID,
Constituents.DisplayName, Constituents.DisplayDate, Constituents.Remarks,
MediaPaths.Path as ThumbPathName, MediaRenditions.ThumbFileName
FROM ConXrefs
INNER JOIN ConXrefDetails on ConXrefs.ConXrefID=ConXrefDetails.ConXrefID
INNER JOIN Constituents on ConXrefDetails.ConstituentID=Constituents.ConstituentID
INNER JOIN Roles on ConXrefs.RoleID=Roles.RoleID
INNER JOIN Sites on ConXrefs.ID=Sites.SiteID AND Sites.IsPublic=1
LEFT JOIN MediaXrefs on Constituents.ConstituentID=MediaXrefs.ID AND MediaXrefs.TableID=23 AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
LEFT JOIN MediaRenditions on MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths on MediaRenditions.ThumbPathID=MediaPaths.PathID
WHERE ConXrefs.TableID=189
AND Constituents.Active=1
AND ConXrefDetails.Unmasked=1
ORDER BY ConXrefs.ID
"""

# Related Published Documents for all Sites
RELATED_PUBLISHED = """
SELECT RefXrefs.ID as SiteID, ReferenceMaster.ReferenceID, ReferenceMaster.Title,
ReferenceMaster.BoilerText, ReferenceMaster.DisplayDate,
ThumbPath.Path as ThumbPathName, MediaRenditions.ThumbFileName,
MainPath.Path as MainPathName, MediaFiles.FileName as MainFileName
FROM Sites
JOIN RefXRefs on Sites.SiteID=RefXRefs.ID
JOIN ReferenceMaster on RefXRefs.ReferenceID=ReferenceMaster.ReferenceID
JOIN MediaXrefs on ReferenceMaster.ReferenceID=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1 AND MediaXrefs.TableID=143
JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
JOIN MediaRenditions on MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID
JOIN MediaFiles on MediaRenditions.RenditionID=MediaFiles.RenditionID
LEFT JOIN MediaPaths AS ThumbPath on MediaRenditions.ThumbPathID=ThumbPath.PathID
LEFT JOIN MediaPaths AS MainPath on MediaFiles.PathID=MainPath.PathID
WHERE MediaRenditions.PrimaryFileID=MediaFiles.FileID
AND MediaTypeID=4
AND Sites.IsPublic=1
ORDER BY SiteID
"""

# Related Media for all Sites
RELATED_MEDIA = """
SELECT MediaXrefs.ID as SiteID, MediaMaster.MediaMasterID, MediaXrefs.PrimaryDisplay,
MediaRenditions.MediaTypeID, MediaMaster.Description, MediaMaster.PublicCaption,
ThumbPath.Path as ThumbPathName, MediaRenditions.ThumbFileName,
MainPath.Path as MainPathName, MediaFiles.FileName as MainFileName
FROM MediaXrefs
INNER JOIN Sites on MediaXrefs.ID=Sites.SiteID AND Sites.IsPublic=1
LEFT JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
LEFT JOIN MediaRenditions on MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaFiles on MediaRenditions.RenditionID=MediaFiles.RenditionID
LEFT JOIN MediaPaths AS ThumbPath on MediaRenditions.ThumbPathID=ThumbPath.PathID
LEFT JOIN MediaPaths AS MainPath on MediaFiles.PathID=MainPath.PathID
WHERE MediaXrefs.TableID=189
AND MediaRenditions.PrimaryFileID=MediaFiles.FileID
ORDER BY MediaXrefs.ID
"""
