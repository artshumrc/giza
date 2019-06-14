
# Site display data
MEDIA = """
SELECT MediaMaster.MediaMasterID, MediaRenditions.RenditionNumber, MediaRenditions.MediaTypeID, MediaRenditions.PrimaryFileID,
replace(replace(MediaMaster.Description, char(10), ''), char(13), ' ') AS Description, MediaMaster.MediaView,
replace(replace(MediaMaster.PublicCaption, char(10), ''), char(13), ' ') AS PublicCaption,
replace(replace(MediaRenditions.Remarks, char(10), ''), char(13), ' ') AS Remarks,
Departments.Department,
ThumbPath.Path AS ThumbPathName, MediaRenditions.ThumbFileName,
MainPath.Path AS MainPathName, MediaFiles.FileName AS MainFileName,
replace(replace(Date.TextEntry, char(10), ''), char(13), ' ') AS DateOfCapture, replace(replace(Problems.TextEntry, char(10), ''), char(13), ' ') AS ProblemsQuestions
FROM MediaMaster
LEFT JOIN Departments ON MediaMaster.DepartmentID=Departments.DepartmentID
LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID IS NOT NULL AND MediaRenditions.MediaTypeID != 4
LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
LEFT JOIN MediaPaths AS ThumbPath ON MediaRenditions.ThumbPathID=ThumbPath.PathID
LEFT JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
LEFT JOIN TextEntries AS Date ON MediaMaster.MediaMasterID=Date.ID AND Date.TableID=318 AND Date.TextTypeID=3
LEFT JOIN TextEntries AS Problems ON MediaMaster.MediaMasterID=Problems.ID AND Problems.TableID=318 AND Problems.TextTypeID=5
WHERE MediaMaster.PublicAccess=1
AND (MediaRenditions.PrimaryFileID = -1 OR MediaRenditions.PrimaryFileID=MediaFiles.FileID)
ORDER BY MediaMaster.MediaMasterID
"""

MET = """
SELECT DISTINCT CN, t.*
FROM gizaCARDTMSThes.dbo.TermMaster tm
JOIN gizaCARDTMSThes.dbo.Terms t ON tm.TermMasterID=t.TermMasterID
WHERE CN LIKE 'AUT.AAA.AAK%'
ORDER BY CN

SELECT MediaMaster.MediaMasterID,
MediaRenditions.MediaTypeID, ThesXrefTypes.ThesXrefType, Terms.TermMasterID, Terms.Term, TermMaster.*
FROM MediaMaster
LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID IS NOT NULL AND MediaRenditions.MediaTypeID != 4
JOIN ThesXrefs ON MediaMaster.MediaMasterID=ThesXrefs.ID AND ThesXrefs.TableID=318
LEFT JOIN ThesXrefTypes ON ThesXrefs.ThesXrefTypeID=ThesXrefTypes.ThesXrefTypeID
LEFT JOIN gizaCARDTMSThes.dbo.Terms Terms ON ThesXrefs.TermID=Terms.TermID
LEFT JOIN gizaCARDTMSThes.dbo.TermMaster ON Terms.TermMasterID=TermMaster.TermMasterID
WHERE MediaMaster.PublicAccess=1
AND MediaMaster.MediaMasterID=21706
"""

# Related Media for all Sites
RELATED_SITES = """
SELECT MediaMaster.MediaMasterID, MediaXrefs.ID AS SiteID, MediaRenditions.MediaTypeID,
Sites.SiteName, Sites.SiteNumber,
ThumbPath.Path AS ThumbPathName, SiteRenditions.ThumbFileName
FROM MediaMaster
JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID IS NOT NULL AND MediaRenditions.MediaTypeID != 4
JOIN MediaXrefs ON MediaMaster.MediaMasterID=MediaXrefs.MediaMasterID AND MediaXrefs.TableID=189
JOIN Sites ON MediaXrefs.ID=Sites.SiteID AND Sites.IsPublic=1
LEFT JOIN MediaXrefs AS SiteXrefs ON Sites.SiteID=SiteXrefs.ID AND SiteXrefs.PrimaryDisplay=1 AND SiteXrefs.TableID=189
LEFT JOIN MediaMaster AS SiteMaster ON SiteXrefs.MediaMasterID=SiteMaster.MediaMasterID AND SiteMaster.PublicAccess=1
LEFT JOIN MediaRenditions AS SiteRenditions ON SiteMaster.MediaMasterID=SiteRenditions.MediaMasterID
LEFT JOIN MediaFiles ON SiteRenditions.RenditionID=MediaFiles.RenditionID AND SiteRenditions.PrimaryFileID=MediaFiles.FileID
LEFT JOIN MediaPaths AS ThumbPath ON SiteRenditions.ThumbPathID=ThumbPath.PathID
WHERE MediaMaster.PublicAccess=1
ORDER BY MediaMaster.MediaMasterID
"""

RELATED_OBJECTS = """
SELECT MediaMaster.MediaMasterID, MediaRenditions.MediaTypeID, MediaXrefs.ID AS ObjectID, Objects.ClassificationID,
replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS Title, Objects.ObjectNumber, Objects.Dated AS ObjectDate,
ThumbPath.Path AS ThumbPathName, ObjectRenditions.ThumbFileName
FROM MediaMaster
JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID IS NOT NULL AND MediaRenditions.MediaTypeID != 4
JOIN MediaXrefs ON MediaMaster.MediaMasterID=MediaXrefs.MediaMasterID AND MediaXrefs.TableID=108
JOIN Objects ON MediaXrefs.ID=Objects.ObjectID AND Objects.PublicAccess=1
JOIN ObjTitles ON Objects.ObjectID=ObjTitles.ObjectID AND ObjTitles.DisplayOrder=1
LEFT JOIN MediaXrefs AS ObjectXrefs ON Objects.ObjectID=ObjectXrefs.ID AND ObjectXrefs.PrimaryDisplay=1 AND ObjectXrefs.TableID=108
LEFT JOIN MediaMaster AS ObjectMaster ON ObjectXrefs.MediaMasterID=ObjectMaster.MediaMasterID AND ObjectMaster.PublicAccess=1
LEFT JOIN MediaRenditions AS ObjectRenditions ON ObjectMaster.MediaMasterID=ObjectRenditions.MediaMasterID
LEFT JOIN MediaFiles ON ObjectRenditions.RenditionID=MediaFiles.RenditionID AND ObjectRenditions.PrimaryFileID=MediaFiles.FileID
LEFT JOIN MediaPaths AS ThumbPath ON ObjectRenditions.ThumbPathID=ThumbPath.PathID
WHERE MediaMaster.PublicAccess=1
ORDER BY MediaMaster.MediaMasterID
"""

RELATED_CONSTITUENTS_1 = """
SELECT DISTINCT MediaMaster.MediaMasterID, MediaRenditions.MediaTypeID, MediaXrefs.ID AS ConstituentID, Constituents.ConstituentTypeID,
Roles.Role, Roles.RoleID,
Constituents.DisplayName, Constituents.DisplayDate, replace(replace(Constituents.Remarks, char(10), ''), char(13), ' ') AS Remarks,
ThumbPath.Path AS ThumbPathName, MediaRenditions.ThumbFileName
FROM MediaMaster
JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID IS NOT NULL AND MediaRenditions.MediaTypeID != 4
JOIN MediaXrefs ON MediaMaster.MediaMasterID=MediaXrefs.MediaMasterID AND MediaXrefs.TableID=23
JOIN Constituents ON MediaXrefs.ID=Constituents.ConstituentID AND Constituents.PublicAccess=1 AND Constituents.ConstituentTypeID>0
JOIN ConXrefDetails ON Constituents.ConstituentID=ConXrefDetails.ConstituentID AND ConXrefDetails.Unmasked=1
JOIN ConXrefs ON ConXrefDetails.ConXrefID=ConXrefs.ConXrefID
JOIN Roles ON ConXrefs.RoleID=Roles.RoleID
LEFT JOIN MediaXrefs AS ConstituentXrefs ON Constituents.ConstituentID=ConstituentXrefs.ID AND ConstituentXrefs.PrimaryDisplay=1 AND ConstituentXrefs.TableID=23
LEFT JOIN MediaMaster AS ConstituentMaster ON ConstituentXrefs.MediaMasterID=ConstituentMaster.MediaMasterID AND ConstituentMaster.PublicAccess=1
LEFT JOIN MediaRenditions AS ConstituentRenditions ON ConstituentMaster.MediaMasterID=ConstituentRenditions.MediaMasterID
LEFT JOIN MediaFiles ON ConstituentRenditions.RenditionID=MediaFiles.RenditionID
LEFT JOIN MediaPaths AS ThumbPath ON ConstituentRenditions.ThumbPathID=ThumbPath.PathID
WHERE MediaMaster.PublicAccess=1
ORDER BY MediaMaster.MediaMasterID
"""

RELATED_CONSTITUENTS_2 = """
SELECT DISTINCT MediaMaster.MediaMasterID, MediaRenditions.MediaTypeID, Constituents.ConstituentID, Constituents.ConstituentTypeID,
Roles.Role, Roles.RoleID,
Constituents.DisplayName, Constituents.DisplayDate, replace(replace(Constituents.Remarks, char(10), ''), char(13), ' ') AS Remarks,
ThumbPath.Path AS ThumbPathName, MediaRenditions.ThumbFileName
FROM MediaMaster
JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID IS NOT NULL AND MediaRenditions.MediaTypeID != 4
JOIN ConXrefs on MediaRenditions.RenditionID=ConXrefs.ID AND ConXrefs.TableID=322
JOIN ConXrefDetails ON ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
JOIN Constituents ON ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.PublicAccess=1 AND Constituents.ConstituentTypeID>0
JOIN Roles ON ConXrefs.RoleID=Roles.RoleID
LEFT JOIN MediaXrefs AS ConstituentXrefs ON Constituents.ConstituentID=ConstituentXrefs.ID AND ConstituentXrefs.PrimaryDisplay=1 AND ConstituentXrefs.TableID=23
LEFT JOIN MediaMaster AS ConstituentMaster ON ConstituentXrefs.MediaMasterID=ConstituentMaster.MediaMasterID AND ConstituentMaster.PublicAccess=1
LEFT JOIN MediaRenditions AS ConstituentRenditions ON ConstituentMaster.MediaMasterID=ConstituentRenditions.MediaMasterID
LEFT JOIN MediaFiles ON ConstituentRenditions.RenditionID=MediaFiles.RenditionID
LEFT JOIN MediaPaths AS ThumbPath ON ConstituentRenditions.ThumbPathID=ThumbPath.PathID
WHERE MediaMaster.PublicAccess=1
ORDER BY MediaMaster.MediaMasterID
"""

RELATED_PUBLISHED = """
SELECT RefXrefs.ID AS MediaMasterID, MasterRenditions.MediaTypeID, ReferenceMaster.ReferenceID, ReferenceMaster.Title,
ReferenceMaster.BoilerText, ReferenceMaster.DisplayDate,
MainPath.Path AS MainPathName, MediaFiles.FileName AS MainFileName
FROM MediaMaster
JOIN MediaRenditions AS MasterRenditions ON MediaMaster.MediaMasterID=MasterRenditions.MediaMasterID
JOIN RefXRefs ON MediaMaster.MediaMasterID=RefXRefs.ID
JOIN ReferenceMaster ON RefXRefs.ReferenceID=ReferenceMaster.ReferenceID AND ReferenceMaster.PublicAccess=1
LEFT JOIN MediaXrefs ON ReferenceMaster.ReferenceID=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1 AND MediaXrefs.TableID=143
LEFT JOIN MediaRenditions ON MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID
LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
LEFT JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
WHERE MediaRenditions.PrimaryFileID=MediaFiles.FileID
AND MediaRenditions.MediaTypeID=4
AND MediaMaster.PublicAccess=1
ORDER BY MediaMaster.MediaMasterID
"""
