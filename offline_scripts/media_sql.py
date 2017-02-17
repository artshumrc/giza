# Site display data
MEDIA = """
SELECT MediaMaster.MediaMasterID, MediaRenditions.MediaTypeID, MediaRenditions.PrimaryFileID,
MediaMaster.Description, MediaMaster.MediaView, MediaMaster.PublicCaption, MediaRenditions.Remarks,
ThumbPath.Path as ThumbPathName, MediaRenditions.ThumbFileName,
MainPath.Path as MainPathName, MediaFiles.FileName as MainFileName,
Date.TextEntry as DateOfCapture, Problems.TextEntry as ProblemsQuestions
FROM MediaMaster
LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID IS NOT NULL AND MediaRenditions.MediaTypeID != 4
LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
LEFT JOIN MediaPaths AS ThumbPath ON MediaRenditions.ThumbPathID=ThumbPath.PathID
LEFT JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
LEFT JOIN TextEntries AS Date on MediaMaster.MediaMasterID=Date.ID AND Date.TableID=318 AND Date.TextTypeID=3
LEFT JOIN TextEntries AS Problems on MediaMaster.MediaMasterID=Problems.ID AND Problems.TableID=318 AND Problems.TextTypeID=5
WHERE MediaMaster.PublicAccess=1
AND (MediaRenditions.PrimaryFileID = -1 OR MediaRenditions.PrimaryFileID=MediaFiles.FileID)
ORDER BY MediaMaster.MediaMasterID
"""

MET = """
SELECT MediaMaster.MediaMasterID,
MediaRenditions.MediaTypeID, ThesXrefTypes.ThesXrefType, Terms.TermMasterID, Terms.Term, TermMaster.*
FROM MediaMaster
LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
JOIN ThesXrefs on MediaMaster.MediaMasterID=ThesXrefs.ID AND ThesXrefs.TableID=318
LEFT JOIN ThesXrefTypes on ThesXrefs.ThesXrefTypeID=ThesXrefTypes.ThesXrefTypeID
LEFT JOIN gizaCARDTMSThes.dbo.Terms Terms on ThesXrefs.TermID=Terms.TermID
LEFT JOIN gizaCARDTMSThes.dbo.TermMaster on Terms.TermMasterID=TermMaster.TermMasterID
WHERE MediaMaster.PublicAccess=1
AND MediaMaster.MediaMasterID=21706
"""

# Related Media for all Sites
RELATED_SITES = """
SELECT MediaMaster.MediaMasterID, MediaXrefs.ID as SiteID, MediaRenditions.MediaTypeID,
Sites.SiteName, Sites.SiteNumber,
ThumbPath.Path as ThumbPathName, SiteRenditions.ThumbFileName
FROM MediaMaster
JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID IS NOT NULL AND MediaRenditions.MediaTypeID != 4
JOIN MediaXrefs on MediaMaster.MediaMasterID=MediaXrefs.MediaMasterID AND MediaXrefs.TableID=189
JOIN Sites on MediaXrefs.ID=Sites.SiteID AND Sites.IsPublic=1
LEFT JOIN MediaXrefs as SiteXrefs on Sites.SiteID=SiteXrefs.ID AND SiteXrefs.PrimaryDisplay=1 AND SiteXrefs.TableID=189
LEFT JOIN MediaMaster as SiteMaster on SiteXrefs.MediaMasterID=SiteMaster.MediaMasterID AND SiteMaster.PublicAccess=1
LEFT JOIN MediaRenditions as SiteRenditions on SiteMaster.MediaMasterID=SiteRenditions.MediaMasterID
LEFT JOIN MediaFiles on SiteRenditions.RenditionID=MediaFiles.RenditionID AND SiteRenditions.PrimaryFileID=MediaFiles.FileID
LEFT JOIN MediaPaths AS ThumbPath on SiteRenditions.ThumbPathID=ThumbPath.PathID
WHERE MediaMaster.PublicAccess=1
ORDER BY MediaMaster.MediaMasterID
"""

RELATED_OBJECTS = """
SELECT MediaMaster.MediaMasterID, MediaRenditions.MediaTypeID, MediaXrefs.ID as ObjectID, Objects.ClassificationID,
ObjTitles.Title, Objects.ObjectNumber, Objects.Dated as ObjectDate,
ThumbPath.Path as ThumbPathName, ObjectRenditions.ThumbFileName
FROM MediaMaster
JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID IS NOT NULL AND MediaRenditions.MediaTypeID != 4
JOIN MediaXrefs on MediaMaster.MediaMasterID=MediaXrefs.MediaMasterID AND MediaXrefs.TableID=108
JOIN Objects on MediaXrefs.ID=Objects.ObjectID AND Objects.PublicAccess=1
JOIN ObjTitles ON Objects.ObjectID=ObjTitles.ObjectID AND ObjTitles.DisplayOrder=1
LEFT JOIN MediaXrefs as ObjectXrefs on Objects.ObjectID=ObjectXrefs.ID AND ObjectXrefs.PrimaryDisplay=1 AND ObjectXrefs.TableID=108
LEFT JOIN MediaMaster as ObjectMaster on ObjectXrefs.MediaMasterID=ObjectMaster.MediaMasterID AND ObjectMaster.PublicAccess=1
LEFT JOIN MediaRenditions as ObjectRenditions on ObjectMaster.MediaMasterID=ObjectRenditions.MediaMasterID
LEFT JOIN MediaFiles on ObjectRenditions.RenditionID=MediaFiles.RenditionID AND ObjectRenditions.PrimaryFileID=MediaFiles.FileID
LEFT JOIN MediaPaths AS ThumbPath on ObjectRenditions.ThumbPathID=ThumbPath.PathID
WHERE MediaMaster.PublicAccess=1
ORDER BY MediaMaster.MediaMasterID
"""

RELATED_CONSTITUENTS = """
SELECT DISTINCT MediaMaster.MediaMasterID, MediaRenditions.MediaTypeID, MediaXrefs.ID as ConstituentID, Constituents.ConstituentTypeID,
Roles.Role, Roles.RoleID,
Constituents.DisplayName, Constituents.DisplayDate, Constituents.Remarks,
ThumbPath.Path as ThumbPathName, MediaRenditions.ThumbFileName
FROM MediaMaster
JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID IS NOT NULL AND MediaRenditions.MediaTypeID != 4
JOIN MediaXrefs on MediaMaster.MediaMasterID=MediaXrefs.MediaMasterID AND MediaXrefs.TableID=23
JOIN Constituents on MediaXrefs.ID=Constituents.ConstituentID AND Constituents.PublicAccess=1 AND Constituents.ConstituentTypeID>0
JOIN ConXrefDetails on Constituents.ConstituentID=ConXrefDetails.ConstituentID AND ConXrefDetails.Unmasked=1
JOIN ConXrefs on ConXrefDetails.ConXrefID=ConXrefs.ConXrefID
JOIN Roles on ConXrefs.RoleID=Roles.RoleID
LEFT JOIN MediaXrefs as ConstituentXrefs on Constituents.ConstituentID=ConstituentXrefs.ID AND ConstituentXrefs.PrimaryDisplay=1 AND ConstituentXrefs.TableID=23
LEFT JOIN MediaMaster as ConstituentMaster on ConstituentXrefs.MediaMasterID=ConstituentMaster.MediaMasterID AND ConstituentMaster.PublicAccess=1
LEFT JOIN MediaRenditions as ConstituentRenditions on ConstituentMaster.MediaMasterID=ConstituentRenditions.MediaMasterID
LEFT JOIN MediaFiles on ConstituentRenditions.RenditionID=MediaFiles.RenditionID
LEFT JOIN MediaPaths AS ThumbPath on ConstituentRenditions.ThumbPathID=ThumbPath.PathID
WHERE MediaMaster.PublicAccess=1
ORDER BY MediaMaster.MediaMasterID
"""

RELATED_PUBLISHED = """
SELECT RefXrefs.ID as MediaMasterID, MasterRenditions.MediaTypeID, ReferenceMaster.ReferenceID, ReferenceMaster.Title,
ReferenceMaster.BoilerText, ReferenceMaster.DisplayDate,
MainPath.Path as MainPathName, MediaFiles.FileName as MainFileName
FROM MediaMaster
JOIN MediaRenditions AS MasterRenditions on MediaMaster.MediaMasterID=MasterRenditions.MediaMasterID
JOIN RefXRefs on MediaMaster.MediaMasterID=RefXRefs.ID
JOIN ReferenceMaster on RefXRefs.ReferenceID=ReferenceMaster.ReferenceID
LEFT JOIN MediaXrefs on ReferenceMaster.ReferenceID=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1 AND MediaXrefs.TableID=143
LEFT JOIN MediaRenditions on MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaFiles on MediaRenditions.RenditionID=MediaFiles.RenditionID
LEFT JOIN MediaPaths AS MainPath on MediaFiles.PathID=MainPath.PathID
WHERE MediaRenditions.PrimaryFileID=MediaFiles.FileID
AND MediaRenditions.MediaTypeID=4
AND MediaMaster.PublicAccess=1
ORDER BY MediaMaster.MediaMasterID
"""
