
# Object display data
CONSTITUENTS = """
SELECT DISTINCT Constituents.ConstituentID AS ID, Constituents.DisplayName, Constituents.DisplayDate,
Constituents.ConstituentTypeID, ConTypes.ConstituentType, replace(replace(Constituents.Remarks, char(10), ''), char(13), ' ') AS Remarks, Terms.Term AS Gender,
Constituents.Institution, Constituents.Nationality, Constituents.BeginDate, Constituents.EndDate
FROM Constituents
LEFT JOIN ConXrefDetails ON Constituents.ConstituentID=ConXrefDetails.ConstituentID AND ConXrefDetails.UnMasked=1
LEFT JOIN ConTypes ON Constituents.ConstituentTypeID=ConTypes.ConstituentTypeID
LEFT JOIN ThesXrefs ON Constituents.ConstituentID=ThesXrefs.ID AND ThesXrefs.ThesXrefTypeID=2 AND ThesXrefs.TableID=23
LEFT JOIN ThesXrefTypes ON ThesXrefs.ThesXrefTypeID=ThesXrefTypes.ThesXrefTypeID
LEFT JOIN gizaCARDTMSThes.dbo.Terms Terms ON ThesXrefs.TermID=Terms.TermID
WHERE Constituents.PublicAccess=1
AND Constituents.ConstituentTypeID>0
ORDER BY Constituents.ConstituentID
"""

# Get Alternate Names for Constituents
ALT_NAMES = """
SELECT Constituents.ConstituentID, Constituents.ConstituentTypeID, ConAltNames.DisplayName, ConAltNames.NameType
FROM Constituents
LEFT JOIN ConAltNames ON Constituents.ConstituentID=ConAltNames.ConstituentID
WHERE Constituents.PublicAccess=1
AND Constituents.ConstituentTypeID>0
AND NameType != 'Primary Name'
ORDER BY Constituents.ConstituentID
"""

# Related Objects for all Constituents
RELATED_OBJECTS = """
SELECT DISTINCT Constituents.ConstituentID, Constituents.ConstituentTypeID, ConXrefs.ID AS ObjectID, replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS Title, Objects.ObjectNumber,
Objects.ClassificationID, Objects.Dated AS ObjectDate,
MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName, MediaFiles.ArchIDNum
FROM ConXrefs
JOIN ConXrefDetails ON ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
JOIN Constituents ON ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.PublicAccess=1 AND Constituents.ConstituentTypeID>0 AND Constituents.Active=1
JOIN Objects ON ConXrefs.ID=Objects.ObjectID AND Objects.PublicAccess=1
JOIN ObjTitles ON Objects.ObjectID=ObjTitles.ObjectID AND ObjTitles.DisplayOrder=1
LEFT JOIN MediaXrefs ON Objects.ObjectID=MediaXrefs.ID AND MediaXrefs.TableID=108 AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
WHERE ConXrefs.TableID=108
AND (
(MediaPaths.Path IS NOT NULL AND MediaRenditions.ThumbFileName IS NOT NULL AND MediaFiles.ArchIDNum IS NOT NULL)
OR (MediaPaths.Path LIKE 'Y:%')
OR (MediaPaths.Path IS NUll AND MediaRenditions.ThumbFileName IS NULL AND MediaFiles.ArchIDNum IS NULL))
ORDER BY Constituents.ConstituentID, ConXrefs.ID
"""

# Related Sites for all Constituents
RELATED_SITES = """
SELECT DISTINCT Constituents.ConstituentID, Constituents.ConstituentTypeID, ConXrefs.ID AS SiteID, Sites.SiteName, Sites.SiteNumber,
MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName, MediaFiles.ArchIDNum
FROM ConXrefs
JOIN ConXrefDetails ON ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
JOIN Constituents ON ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.PublicAccess=1 AND Constituents.ConstituentTypeID>0 AND Constituents.Active=1
JOIN Sites ON ConXrefs.ID=Sites.SiteID AND Sites.IsPublic=1
LEFT JOIN MediaXrefs ON Sites.SiteID=MediaXrefs.ID AND MediaXrefs.TableID=189 AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
WHERE ConXrefs.TableID=189
AND (
(MediaPaths.Path IS NOT NULL AND MediaRenditions.ThumbFileName IS NOT NULL AND MediaFiles.ArchIDNum IS NOT NULL)
OR (MediaPaths.Path LIKE 'Y:%')
OR (MediaPaths.Path IS NUll AND MediaRenditions.ThumbFileName IS NULL AND MediaFiles.ArchIDNum IS NULL))
ORDER BY Constituents.ConstituentID, ConXrefs.ID
"""

# Related Published Documents for all Constituents
RELATED_PUBLISHED = """
SELECT DISTINCT Constituents.ConstituentID, Constituents.ConstituentTypeID, ReferenceMaster.ReferenceID, ReferenceMaster.Title, ReferenceMaster.BoilerText, ReferenceMaster.DisplayDate,
MainPath.Path AS MainPathName, MediaFiles.FileName AS MainFileName
FROM ConXrefs
JOIN ConXrefDetails ON ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
JOIN Constituents ON ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.PublicAccess=1 AND Constituents.ConstituentTypeID>0
JOIN ReferenceMaster ON ConXrefs.ID=ReferenceMaster.ReferenceID AND ReferenceMaster.PublicAccess=1
LEFT JOIN MediaXrefs ON ReferenceMaster.ReferenceID=MediaXrefs.ID AND MediaXrefs.TableID=143 AND MediaXrefs.PrimaryDisplay=1
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
LEFT JOIN MediaRenditions ON MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
LEFT JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
WHERE ConXrefs.TableID=143
AND MediaRenditions.PrimaryFileID=MediaFiles.FileID
AND MediaTypeID=4
ORDER BY Constituents.ConstituentID
"""

# Related Media for all Constituents
RELATED_MEDIA = """
SELECT DISTINCT MediaXrefs.ID AS ID, Constituents.ConstituentTypeID,  MediaMaster.MediaMasterID, Objects.ClassificationID, MediaXrefs.PrimaryDisplay,
MediaRenditions.MediaTypeID, MediaRenditions.RenditionNumber, replace(replace(MediaMaster.Description, char(10), ''), char(13), ' ') AS Description,
MediaMaster.MediaView, replace(replace(MediaMaster.PublicCaption, char(10), ''), char(13), ' ') AS PublicCaption,
ThumbPath.Path AS ThumbPathName, MediaRenditions.ThumbFileName,
MainPath.Path AS MainPathName, MediaFiles.FileName AS MainFileName, MediaFiles.ArchIDNum
FROM MediaXrefs
JOIN Constituents ON MediaXrefs.ID=Constituents.ConstituentID AND Constituents.PublicAccess=1 AND Constituents.ConstituentTypeID>0
LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN Objects ON MediaXrefs.ID=Objects.ObjectID AND Objects.PublicAccess=1
LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
LEFT JOIN MediaPaths AS ThumbPath ON MediaRenditions.ThumbPathID=ThumbPath.PathID
LEFT JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
WHERE MediaXrefs.TableID=23
AND MediaRenditions.PrimaryFileID=MediaFiles.FileID
ORDER BY MediaXrefs.ID, MediaMaster.MediaMasterID
"""
