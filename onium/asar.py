import io
import os
import json
import errno
import struct
import shutil


### WARNING ### 
### SUPPORT FOR UNPACKED FILES IS VERY PARTIAL. SOME FILES ARE MODIFIED IN PLACE INSTEAD OF TO A SIDE PROEJCT
### REMOVE WHEN ACTUALLY FIXED

def round_up(i, m):
    """Rounds up ``i`` to the next multiple of ``m``.

    ``m`` is assumed to be a power of two.
    """
    return (i + m - 1) & ~(m - 1)

def forward_path_split(path):
    return ([''] + os.path.normpath(path).split(os.path.sep,1) )[-2:]


class Asar:

    """Represents an asar file.

    You probably want to use the :meth:`.open` or :meth:`.from_path`
    class methods instead of creating an instance of this class.

    Attributes
    ----------
    path : str
        Path of this asar file on disk.
        If :meth:`.from_path` is used, this is just
        the path static_method to it.
    fp : File-like object
        Contains the data for this asar file.
    header : dict
        Dictionary used for random file access.
    base_offset : int
        Indicates where the asar file header ends.
    """

    def __init__(self, path, fp, header, base_offset):
        self.path = path
        self.fp = fp
        self.header = header
        self.base_offset = base_offset

    @classmethod
    def open(cls, path):
        """Decodes the asar file from the given ``path``.

        You should use the context manager interface here,
        to automatically close the file object when you're done with it, i.e.

        .. code-block:: python

            with Asar.open('./something.asar') as a:
                a.extract('./something_dir')

        Parameters
        ----------
        path : str
            Path of the file to be decoded.
        """
        fp = open(path, 'rb')

        # decode header
        # NOTE: we only really care about the last value here.
        data_size, header_size, header_object_size, header_string_size = struct.unpack('<4I', fp.read(16))

        header_json = fp.read(header_string_size).decode('utf-8')

        return cls(
            path=path,
            fp=fp,
            header=json.loads(header_json),
            base_offset=round_up(16 + header_string_size, 4)
        )


    @staticmethod
    def _build(header, concatenated_files):
        header_json = json.dumps(header, sort_keys=True, separators=(',', ':')).encode('utf-8')

        # TODO: using known constants here for now (laziness)...
        #       we likely need to calc these, but as far as discord goes we haven't needed it.
        header_string_size = len(header_json)
        data_size = 4 # uint32 size
        aligned_size = round_up(header_string_size, data_size)
        header_size = aligned_size + 8
        header_object_size = aligned_size + data_size

        # pad remaining space with NULLs
        diff = aligned_size - header_string_size
        header_json = header_json + b'\0' * (diff) if diff else header_json

        fp = io.BytesIO()
        fp.write(struct.pack('<4I', data_size, header_size, header_object_size, header_string_size))
        fp.write(header_json)
        fp.write(concatenated_files)

        return {'path':None,
                'fp':fp,
                'header':header,
                'base_offset':round_up(16 + header_string_size, 4)
        }

    @classmethod
    def from_path(cls, path):
        """Creates an asar file using the given ``path``.

        When this is used, the ``fp`` attribute of the returned instance
        will be a :class:`io.BytesIO` object, so it's not written to a file.
        You have to do something like:

        .. code-block:: python

            with Asar.from_path('./something_dir') as a:
                with open('./something.asar', 'wb') as f:
                    a.fp.seek(0) # just making sure we're at the start of the file
                    f.write(a.fp.read())

        You cannot exclude files/folders from being packed yet.

        Parameters
        ----------
        path : str
            Path to walk into, recursively, and pack
            into an asar file.
        """

        def _path_to_dict(path, buf):
            result = {'files': {}}

            for f in os.scandir(path):
                if os.path.isdir(f.path):
                    result['files'][f.name] = _path_to_dict(f.path)
                elif f.is_symlink():
                    result['files'][f.name] = {
                        'link': os.path.realpath(f.name)
                    }
                else:
                    size = f.stat().st_size

                    result['files'][f.name] = {
                        'size': size,
                        'offset': str(buf.tell())
                    }

                    with open(f.path, 'rb') as fp:
                        buf.write(fp.read())

            return result

        buf = io.BytesIO()
        header = _path_to_dict(path, buf)
        return cls(**cls._build(header, concatenated_files))

    def __setitem__(self, name, content):
        FILE_IS_UNPACKED = object()
        def _inline_header(header, fp, base_offset):
            new_dict = {"files": {} }
            for (k, v) in header['files'].items():
                if "files" in v:
                    new_dict['files'][k] = _inline_header(v, fp, base_offset)
                elif "link" in v or "unpacked" in v: #Ignore pre-set files
                    new_dict['files'][k] = v
                elif "content" in v: # ignore those items we've already set
                    new_dict['files'][k] = v
                else:
                    d = {}
                    new_dict['files'][k] = d
                    fp.seek(base_offset + int(v['offset']))
                    d['content'] = fp.read(v['size'])
            return new_dict

        def _reflat_header(header, buf):
            for (k,v) in header['files'].items():
                if "files" in v:
                    _reflat_header(v, buf)
                elif ("content" in v):
                    v['size'] = len(v['content'])
                    v['offset'] = str(buf.tell())
                    buf.write(v['content'])
                    del v['content']

        def _set_inlined_header(header, item, content):
            (p,n) = forward_path_split(item)
            if not 'files' in header:
                raise Exception("error modifying dictionary")

            if (p != ''):
                # 'files' in root key
                # Either P doesn't exist, or it exists and isn't a directory. 
                if not p in header['files'] or not 'files' in header['files'][p]:
                    header['files'][p] = {'files':{}}
                return _set_inlined_header(header['files'][p], n, content)
            else: # we're at the target item
                if 'unpacked' in header['files'][n]:
                    return FILE_IS_UNPACKED
                else:
                    header['files'][n] = { "content" : content } 
                    return None



        if (type(content) != bytes):
            raise Exception("content must be gives as a bytes object")

        inline = _set_inlined_header(self.header, name, content)
        if (inline == FILE_IS_UNPACKED):
           if self.path is None:
               raise Exception ("Don't support unpacked with non-physical files")
           file_path = os.path.join(self.path + ".unpacked", os.path.normpath(name))
           open(file_path,'wb').write(content)
        else:
            header = _inline_header(self.header, self.fp, self.base_offset)
            _set_inlined_header(header, name, content)
            buf = io.BytesIO()
            _reflat_header(header, buf)

            out = self._build(header, buf.getvalue())
            self.header = out['header']
            self.fp = out['fp']
            self.base_offset = out['base_offset']
            self.path = None

    def __getitem__(self, item):
        FILE_IS_UNPACKED = object()
        def _rec_get_item(header, item, buf, base_offset):
            (p,n) = forward_path_split(item)
            if not 'files' in header:
                raise Exception("error in header")
            if p != '':
                if not p in header['files'] or not 'files' in header['files'][p]:
                    raise Exception("item not found")
                return _rec_get_item(header['files'][p], n, buf, base_offset)
            else: # we're at target item
                if 'unpacked' in header['files'][n]: 
                    # handle unpacked files modification
                    return FILE_IS_UNPACKED
                elif not 'offset' in header['files'][n]:
                    raise Exception("Path isn't a file")
                buf.seek(base_offset + int(header['files'][n]['offset']))
                return buf.read(header['files'][n]['size'])

        ret = _rec_get_item(self.header, item, self.fp, self.base_offset)
        if ret is not FILE_IS_UNPACKED: return ret
        if self.path is None: 
            raise Exception ("Don't support unpacked with non-physical files")
        file_path = os.path.join(self.path + ".unpacked", os.path.normpath(item))
        return open(file_path,'rb').read()


    def _copy_unpacked_file(self, source, destination):
        """Copies an unpacked file to where the asar is extracted to.

        An example:

            .
             test.asar
             test.asar.unpacked
                abcd.png
                efgh.jpg
                test_subdir
                    xyz.wav

        If we are extracting ``test.asar`` to a folder called ``test_extracted``,
        not only the files concatenated in the asar will go there, but also
        the ones inside the ``*.unpacked`` folder too.

        That is, after extraction, the previous example will look like this:

            .
            test.asar
            test.asar.unpacked
              ...
            test_extracted
                whatever_was_inside_the_asar.js
                junk.js
                abcd.png
                efgh.jpg
                test_subdir
                    xyz.wav

        In the asar header, they will show up without an offset, and ``"unpacked": true``.

        Currently, if the expected directory doesn't already exist (or the file isn't there),
        a message is printed to stdout. It could be logged in a smarter way but that's a TODO.

        Parameters
        ----------
        source : str
            Path of the file to locate and copy
        destination : str
            Destination folder to copy file into
        """
        unpacked_dir = self.path + '.unpacked'
        if not os.path.isdir(unpacked_dir):
            print("Couldn't copy file {}, no extracted directory".format(source))
            return

        src = os.path.join(unpacked_dir, source)
        if not os.path.exists(src):
            print("Couldn't copy file {}, doesn't exist".format(src))
            return

        dest = os.path.join(destination, source)
        shutil.copyfile(src, dest)

    def _extract_file(self, source, info, destination):
        """Locates and writes to disk a given file in the asar archive.

        Parameters
        ----------
        source : str
            Path of the file to write to disk
        info : dict
            Contains offset and size if applicable.
            If offset is not given, the file is assumed to be
            sitting outside of the asar, unpacked.
        destination : str
            Destination folder to write file into

        See Also
        --------
        :meth:`._copy_unpacked_file`
        """
        if 'offset' not in info:
            self._copy_unpacked_file(source, destination)
            return

        self.fp.seek(self.base_offset + int(info['offset']))
        r = self.fp.read(int(info['size']))

        dest = os.path.join(destination, source)
        with open(dest, 'wb') as f:
            f.write(r)

    def _extract_link(self, source, link, destination):
        """Creates a symbolic link to a file we extracted (or will extract).

        Parameters
        ----------
        source : str
            Path of the symlink to create
        link : str
            Path of the file the symlink should point to
        destination : str
            Destination folder to create the symlink into
        """
        dest_filename = os.path.normpath(os.path.join(destination, source))
        link_src_path = os.path.dirname(os.path.join(destination, link))
        link_to = os.path.join(link_src_path, os.path.basename(link))

        try:
            os.symlink(link_to, dest_filename)
        except OSError as e:
            if e.errno == errno.EXIST:
                os.unlink(dest_filename)
                os.symlink(link_to, dest_filename)
            else:
                raise e

    def _extract_directory(self, source, files, destination):
        """Extracts all the files in a given directory.

        If a sub-directory is found, this calls itself as necessary.

        Parameters
        ----------
        source : str
            Path of the directory
        files : dict
            Maps a file/folder name to another dictionary,
            containing either file information,
            or more files.
        destination : str
            Where the files in this folder should go to
        """
        dest = os.path.normpath(os.path.join(destination, source))

        if not os.path.exists(dest):
            os.makedirs(dest)

        for name, info in files.items():
            item_path = os.path.join(source, name)

            if 'files' in info:
                self._extract_directory(item_path, info['files'], destination)
            elif 'link' in info:
                self._extract_link(item_path, info['link'], destination)
            else:
                self._extract_file(item_path, info, destination)

    def extract(self, path):
        """Extracts this asar file to ``path``.

        Parameters
        ----------
        path : str
            Destination of extracted asar file.
        """
        if os.path.exists(path):
            raise FileExistsError()

        self._extract_directory('.', self.header['files'], path)

    def save(self, fn):
        self.fp.seek(0) # just making sure we're at the start of the file
        data = self.fp.read()
        with open(fn, 'wb') as f:
            self.fp.seek(0) # just making sure we're at the start of the file
            f.write(data)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.fp.close()




