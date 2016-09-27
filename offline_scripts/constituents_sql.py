# Object display data
CONSTITUENTS = """
SELECT DISTINCT Constituents.ConstituentID as ID, Constituents.DisplayName, Constituents.DisplayDate,
Constituents.ConstituentTypeID, ConTypes.ConstituentType, Constituents.Remarks, Terms.Term as Gender
FROM Constituents
LEFT JOIN ConXrefDetails on Constituents.ConstituentID=ConXrefDetails.ConstituentID AND ConXrefDetails.UnMasked=1
LEFT JOIN ConTypes on Constituents.ConstituentTypeID=ConTypes.ConstituentTypeID
LEFT JOIN ThesXrefs on Constituents.ConstituentID=ThesXrefs.ID AND ThesXrefs.ThesXrefTypeID=2 AND ThesXrefs.TableID=23
LEFT JOIN ThesXrefTypes on ThesXrefs.ThesXrefTypeID=ThesXrefTypes.ThesXrefTypeID
LEFT JOIN gizaCARDTMSThes.dbo.Terms Terms on ThesXrefs.TermID=Terms.TermID
WHERE Constituents.PublicAccess=1
ORDER BY Constituents.ConstituentID
"""

# Get Alternate Names for Constituents
ALT_NAMES = """
SELECT Constituents.ConstituentID, Constituents.ConstituentTypeID, ConAltNames.DisplayName
FROM Constituents
LEFT JOIN ConAltNames on Constituents.ConstituentID=ConAltNames.ConstituentID
ORDER BY Constituents.ConstituentID
"""

# Related Objects for all Constituents
RELATED_OBJECTS = """
SELECT Constituents.ConstituentID, Constituents.ConstituentTypeID, ConXrefs.ID as ObjectID, ObjTitles.Title, Objects.ObjectNumber,
Objects.ClassificationID, Objects.Dated as ObjectDate,
MediaPaths.Path as ThumbPathName, MediaRenditions.ThumbFileName
FROM ConXrefs
JOIN ConXrefDetails on ConXrefs.ConXrefID=ConXrefDetails.ConXrefID
JOIN Constituents on ConXrefDetails.ConstituentID=Constituents.ConstituentID
JOIN Objects on ConXrefs.ID=Objects.ObjectID
JOIN ObjTitles ON Objects.ObjectID=ObjTitles.ObjectID
JOIN MediaXrefs on Constituents.ConstituentID=MediaXrefs.ID
JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
JOIN MediaRenditions on MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
JOIN MediaPaths on MediaRenditions.ThumbPathID=MediaPaths.PathID
WHERE ConXrefs.TableID=108
AND Constituents.Active=1
AND ConXrefDetails.Unmasked=1
AND MediaXrefs.TableID=23
AND MediaXrefs.PrimaryDisplay=1
ORDER BY Constituents.ConstituentID
"""

# Related Sites for all Constituents
RELATED_SITES = """
SELECT Constituents.ConstituentID, Constituents.ConstituentTypeID, ConXrefs.ID as SiteID, Sites.SiteName, Sites.SiteNumber,
MediaPaths.Path as ThumbPathName, MediaRenditions.ThumbFileName
FROM ConXrefs
LEFT JOIN ConXrefDetails on ConXrefs.ConXrefID=ConXrefDetails.ConXrefID
LEFT JOIN Constituents on ConXrefDetails.ConstituentID=Constituents.ConstituentID
LEFT JOIN Sites on ConXrefs.ID=Sites.SiteID
LEFT JOIN MediaXrefs on Constituents.ConstituentID=MediaXrefs.ID
LEFT JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
LEFT JOIN MediaRenditions on MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaPaths on MediaRenditions.ThumbPathID=MediaPaths.PathID
WHERE ConXrefs.TableID=189
AND Constituents.Active=1
AND ConXrefDetails.Unmasked=1
AND MediaXrefs.TableID=23
AND MediaXrefs.PrimaryDisplay=1
ORDER BY Constituents.ConstituentID
"""

# Related Published Documents for all Constituents
RELATED_PUBLISHED = """
SELECT RefXrefs.ID as ID, Constituents.ConstituentTypeID, ReferenceMaster.ReferenceID, ReferenceMaster.Title, ReferenceMaster.BoilerText, ReferenceMaster.DisplayDate,
MainPath.Path as MainPathName, MediaFiles.FileName as MainFileName
FROM Constituents
JOIN RefXRefs on Constituents.ConstituentID=RefXRefs.ID
JOIN ReferenceMaster on RefXrefs.ReferenceID=ReferenceMaster.ReferenceID
JOIN MediaXrefs on ReferenceMaster.ReferenceID=MediaXrefs.ID
JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
JOIN MediaRenditions on MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID
JOIN MediaFiles on MediaRenditions.RenditionID=MediaFiles.RenditionID
JOIN MediaPaths AS MainPath on MediaFiles.PathID=MainPath.PathID
WHERE MediaXrefs.PrimaryDisplay=1
AND MediaMaster.PublicAccess=1
AND MediaRenditions.PrimaryFileID=MediaFiles.FileID
AND MediaXrefs.TableID=143
AND MediaTypeID=4
ORDER BY Constituents.ConstituentID
"""

# Related Media for all Constituents
RELATED_MEDIA = """
SELECT MediaXrefs.ID as ID, Constituents.ConstituentTypeID,  MediaMaster.MediaMasterID, Objects.ClassificationID, MediaXrefs.PrimaryDisplay,
MediaRenditions.MediaTypeID, MediaMaster.Description, MediaMaster.PublicCaption,
ThumbPath.Path as ThumbPathName, MediaRenditions.ThumbFileName,
MainPath.Path as MainPathName, MediaFiles.FileName as MainFileName
FROM MediaXrefs
JOIN Constituents on MediaXrefs.ID=Constituents.ConstituentID
LEFT JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
LEFT JOIN MediaRenditions on MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN Objects on MediaXrefs.ID=Objects.ObjectID
LEFT JOIN MediaFiles on MediaRenditions.RenditionID=MediaFiles.RenditionID
LEFT JOIN MediaPaths AS ThumbPath on MediaRenditions.ThumbPathID=ThumbPath.PathID
LEFT JOIN MediaPaths AS MainPath on MediaFiles.PathID=MainPath.PathID
WHERE MediaXrefs.TableID=23
AND MediaMaster.PublicAccess=1
AND MediaRenditions.PrimaryFileID=MediaFiles.FileID
ORDER BY MediaXrefs.ID
"""