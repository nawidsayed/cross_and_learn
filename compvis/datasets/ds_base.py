import torch.utils.data as data_old
import os
import numpy as np
import _pickle as pickle
from PIL import Image
import torch
import os
from io import BytesIO
import compvis.data as data

__all__ = ['Dataset_Image', 'Dataset_RGB', 'Dataset_OF', 'Dataset_COD', 
'Dataset_def', 'Dataset_fm', 'Dataset_sl']

# Resizes image to at least (320, 240) and then crops for that size
def prep_image(path):
	img = Image.open(path)
	img.load()
	w, h = img.size
	if 3*w < 4*h:
		wp = 320
		hp = int(320 * h / w)
	else:
		hp = 240
		wp = int(240 * w / h)
	img = img.resize((wp, hp), resample=Image.BILINEAR)
	w, h = wp, hp
	tw, th = 320, 240
	x1 = int(round((w - tw) / 2.))
	y1 = int(round((h - th) / 2.))
	img = img.crop((x1, y1, x1 + tw, y1 + th))
	return img

def sample_high_motion(list_mag, num_frames, mode=1):
	list_mag_cum = [0]
	cum = 0
	for mag in list_mag:
		cum += mag ** mode
		list_mag_cum.append(cum)
	list_mag_nf = []
	for i in range(len(list_mag)-num_frames+1):
		mag_nf = list_mag_cum[i+num_frames] - list_mag_cum[i]
		list_mag_nf.append(mag_nf)
	list_mag_nf_cum = [0]
	cum = 0
	for mag_nf in list_mag_nf:
		cum += mag_nf
		list_mag_nf_cum.append(cum)	
	rand = np.random.uniform(list_mag_nf_cum[0], list_mag_nf_cum[-1])
	ind_frame = 0
	while rand >= list_mag_nf_cum[ind_frame+1]:
		ind_frame += 1
	return ind_frame

# TODO use first sample_indices

# def sample_indices(num_frames, spacing):
# 	spacing -= 1
# 	indices = [0]
# 	left = np.arange(spacing+1, num_frames-3*spacing)
# 	np.random.shuffle(left)
# 	left = left[:3]
# 	left.sort()
# 	for i in range(3):
# 		left[i] += i * spacing
# 	left = list(left)
# 	indices += left
# 	indices.append(num_frames)
# 	return np.array(indices)


# def sample_indices(num_frames, spacing):
# 	center = int(num_frames/2)
# 	spacing -= 1
# 	indices = [0, center-1, center, center+1, num_frames]
# 	return np.array(indices)

# stack is a list only containing the stack
def rand_timeflip(stack, rand, channels):
	if rand > 0.5:		
		stack_rev = []
		stack = stack[0]
		num_frames = int(stack.size()[0] / channels)
		for i in range(num_frames):
			s = stack[channels*i:channels*(i+1)]
			s = -s
			stack_rev.insert(0, s)
		stack_rev = [torch.cat(stack_rev, 0)]
		return stack_rev
	return stack

class Base_Dataset(data.Dataset):
	data_cache = None
	def __init__(self, infos, train=True):
		self.infos = infos
		for i, info in enumerate(self.infos):
			info.num_info = i
		self.train = train
		self.len = 0
		for info in self.infos:
			self.len += len(info)

	def __len__(self):
		return self.len

	def get_info_index(self, index):
		for info in self.infos:
			length = len(info)
			if length <= index:
				index -= length
			else:
				return info, index

	def _set_data_cache(self):
		self.data_cache = {}
		for info in self.infos:
			self.data_cache.update(info.get_data_cache())

	def set_index_list(self, index_list):
		self.len = len(index_list)
		self.index_list = index_list

	def _prep_index(self, index):
		if not hasattr(self, 'index_list'):
			return index
		else:
			return self.index_list[index]

	def get_sample(self, index):
		raise NotImplementedError('get_sample() not implemented in Base_Dataset')

class Dataset_Image(Base_Dataset):
	def __init__(self, infos, train=True, transform=None):	
		super(Dataset_Image, self).__init__(infos, train=train)
		self.transform = transform

	def __getitem__(self, index):
		index = self._prep_index(index)
		info, index = self.get_info_index(index)
		path_frame = info.get_image_path(index)
		return path_frame, info.get_label(index)

	def preprocess(self, raw):
		raw = list(raw)
		if len(raw) == 2:
			path_frame, label = raw
			random = np.random.RandomState()
		else:
			path_frame, label, random = raw
		img = prep_image(path_frame)
		img = self.transform(img, random)
		images = []
		if isinstance(img, list): 
			images += img
		else:
			images.append(img)
		num = len(images)
		label = num * [label] 
		return images, label

	def get_sample(self, index):
		return self.preprocess(self[index])[0][0]

class Dataset_RGB(Base_Dataset):
	def __init__(self, infos, train=True, transform=None, num_test=5):	
		super(Dataset_RGB, self).__init__(infos, train=train)
		self.transform = transform
		self.num_test = num_test

	def __getitem__(self, index):
		index = self._prep_index(index)
		if isinstance(index, tuple):
			index, ind_frame = index
		else:
			ind_frame = None
		info, index = self.get_info_index(index)
		if ind_frame is not None:
			ind_frames = np.array([ind_frame]).astype(np.int32)
		else:
			num_rgb = info.get_num_rgb(index)
			if self.train:
				ind_frames = np.array([np.random.randint(0, num_rgb)]).astype(np.int32)
			else:
				if self.num_test >= 0:
					num_test = self.num_test
					ind_frames = np.linspace(0, num_rgb-1, num_test).astype(np.int32)
				else:
					num_test = -self.num_test
					ind_frames = np.arange(0, num_rgb, num_test).astype(np.int32)

		path_frames = []
		for ind_frame in ind_frames:
			path_frames.append(info.get_rgb_path(index, ind_frame))
		label_offset = info.num_info * 100000
		return path_frames, info.get_label(index) + label_offset

	def preprocess(self, raw):
		raw = list(raw)
		if len(raw) == 2:
			path_frames, label = raw
			random = np.random.RandomState()
		else:
			path_frames, label, random = raw
		randomstate = random.get_state() 
		images = []
		for path_frame in path_frames:
			img = prep_image(path_frame)
			random.set_state(randomstate)
			img = self.transform(img, random)
			if isinstance(img, list): 
				images += img
			else:
				images.append(img)
		num = len(images)
		label = num * [label] 
		return images, label

	def get_sample(self, index):
		return self.preprocess(self[index])[0][0]

class Dataset_OF(Base_Dataset):
	def __init__(self, infos, train=True, transform=None, num_test=5, num_frames=12, transform_rgb=None,
		remove_motion=False, cutout_center=0, high_motion=False, time_flip=False):
		super(Dataset_OF, self).__init__(infos, train=train)
		self.transform = transform
		self.num_test = num_test
		self.num_frames = num_frames
		self.transform_rgb = transform_rgb
		self.remove_motion = remove_motion
		self.cutout_center = cutout_center
		self.high_motion = high_motion
		self.time_flip = time_flip

	def __getitem__(self, index):
		index = self._prep_index(index)
		if isinstance(index, tuple):
			index, ind_frame_first = index
		else:
			ind_frame_first = None
		info, index = self.get_info_index(index)
		if ind_frame_first is not None:
			ind_frames_first = np.array([ind_frame_first]).astype(np.int32)
		else:
			num_rgb = info.get_num_rgb(index)
			if self.train:
				list_mag = info.get_mag(index)
				ind_frame_first = sample_high_motion(list_mag, self.num_frames, mode=self.high_motion)
				ind_frames_first = np.array([ind_frame_first]).astype(np.int32)
			else:
				if self.num_test >= 0:
					num_test = self.num_test
					ind_frames_first = np.linspace(0, num_rgb-self.num_frames-1, num_test).astype(np.int32)
				else:
					num_test = -self.num_test
					ind_frames_first = np.arange(0, num_rgb-self.num_frames, num_test).astype(np.int32)

		buffers_norms = []
		path_frames = []
		for ind_frame_first in ind_frames_first:
			if self.transform_rgb is not None:
				path_frames.append(info.get_rgb_path(index, ind_frame_first))
			for i in range(self.num_frames):
				for direction in ['x', 'y']:
					ind_frame = ind_frame_first + i
					key_of = info.get_of_key(index, ind_frame, direction)
					buf = self._get_buf(key_of)
					norm = info.get_norm(index, ind_frame)
					buffers_norms.append((buf, norm))
		if path_frames == []:
			return buffers_norms, info.get_label(index)
		else:
			return path_frames, buffers_norms, info.get_label(index)

	def preprocess(self, raw):
		raw = list(raw)
		if self.transform_rgb is None:
			if len(raw) == 2:
				buffers_norms, label = raw
				random = np.random.RandomState()
			else:
				buffers_norms, label, random = raw
		else:
			path_frames, buffers_norms, label = raw
			random = np.random.RandomState()
		randomstate = random.get_state() 
		rand_flip = 0
		if self.time_flip and self.train:
			rand_flip = np.random.rand()
		images = []
		for buf, norm in buffers_norms:
			buf.seek(0)
			img = Image.open(buf)
			img.load()
			random.set_state(randomstate)
			img = self.transform(img, random)
			if isinstance(img, list):
				num_crops = len(img)
				for flow in img:
					images.append(flow * norm)
			else:
				num_crops = 1
				images.append(img * norm)
		num_samples = int(len(images) / (2*self.num_frames*num_crops))
		flows = []
		for i in range(num_samples):
			for j in range(num_crops):
				flow = torch.cat(images[j::num_crops][(2*self.num_frames)*i:(2*self.num_frames)*(i+1)], 0)
				if self.remove_motion:
					flow_nomot = flow.clone()
					for k in range(self.num_frames):
						flow_nomot_single = torch.sqrt(flow[2*k]**2 + flow[2*k+1]**2)
						flow_nomot[2*k] = flow_nomot_single
						flow_nomot[2*k+1] = flow_nomot_single
					flow = flow_nomot
				if self.cutout_center != 0:
					center = int(self.num_frames)
					space = self.cutout_center
					flow[center-space:center+space] = 0
				flows.append(flow)
		flows = rand_timeflip(flows, rand_flip, 2)
		num = len(flows)
		label = num * [label]
		if self.transform_rgb is None:
			return flows, label		
		else:
			images = []
			for path_frame in path_frames:
				img = prep_image(path_frame)
				random.set_state(randomstate)
				img = self.transform_rgb(img, random)
				if isinstance(img, list): 
					images += img
				else:
					images.append(img)
			return flows, label, images

	def get_sample(self, index):
		return self.preprocess(self[index])[0][0]

	def _get_buf(self, name):
		if self.data_cache is None:
			self._set_data_cache()
		return self.data_cache[name]

class Dataset_COD(Base_Dataset):
	def __init__(self, infos, train=True, transform=None, num_test=5, num_frames=12, cutout_center=0,
		nodiff=False, time_flip=False):	
		super(Dataset_COD, self).__init__(infos, train=train)
		self.transform = transform
		self.num_test = num_test
		self.num_frames = num_frames
		self.cutout_center = cutout_center
		self.nodiff = nodiff
		self.time_flip = time_flip

	def __getitem__(self, index):
		index = self._prep_index(index)
		if isinstance(index, tuple):
			index, ind_frame_first = index
		else:
			ind_frame_first = None
		info, index = self.get_info_index(index)
		if ind_frame_first is not None:
			ind_frames_first = np.array([ind_frame_first]).astype(np.int32)
		else:
			num_rgb = info.get_num_rgb(index)
			if self.train:
				ind_frames_first = np.array([np.random.randint(0, num_rgb-self.num_frames)]).astype(np.int32)
			else:
				if self.num_test >= 0:
					num_test = self.num_test
					ind_frames_first = np.linspace(0, num_rgb-self.num_frames-1, num_test).astype(np.int32)
				else:
					num_test = -self.num_test
					ind_frames_first = np.arange(0, num_rgb-self.num_frames, num_test).astype(np.int32)
		path_frames = []
		for ind_frame_first in ind_frames_first:
			for i in range(self.num_frames + 1):
				ind_frame = ind_frame_first + i
				path_frames.append(info.get_rgb_path(index, ind_frame))
		return path_frames, info.get_label(index)

	def preprocess(self, raw):
		raw = list(raw)
		if len(raw) == 2:
			path_frames, label = raw
			random = np.random.RandomState()
		else:
			path_frames, label, random = raw
		randomstate = random.get_state()
		rand_flip = 0
		if self.time_flip and self.train:
			rand_flip = np.random.rand() 
		images = []
		for path_frame in path_frames:
			img = prep_image(path_frame)
			random.set_state(randomstate)
			img = self.transform(img, random)
			if isinstance(img, list): 
				num_crops = len(img)
				images += img
			else:
				images.append(img)
				num_crops = 1
		num_samples = int(len(images) / ((self.num_frames+1)*num_crops))
		cods = []
		for i in range(num_samples):
			for j in range(num_crops):
				coi = torch.cat(images[j::num_crops][(self.num_frames+1)*i:(self.num_frames+1)*(i+1)], 0)
				cod = torch.Tensor(coi.size(0)-3, coi.size(1), coi.size(2))
				for k in range(self.num_frames):
					cod[3*k:3*(k+1)] = coi[3*(k+1):3*(k+2)] - coi[3*k:3*(k+1)]
					if self.nodiff:
						cod[3*k:3*(k+1)] = coi[3*k:3*(k+1)]
				if self.cutout_center != 0:
					center = int(self.num_frames / 2) * 3
					space = int(self.cutout_center / 2) * 3
					cod[center-space:center+space] = 0
				cods.append(cod)
		cods = rand_timeflip(cods, rand_flip, 3)
		num = len(cods)
		label = num * [label]
		return cods, label		

	def get_sample(self, index):
		return self.preprocess(self[index])[0][0]

class Dataset_def(Base_Dataset):
	def __init__(self, infos, train=True, transform_rgb=None, transform_of=None, num_frames=12, 
		remove_motion=False, cutout_center=0, high_motion=False, time_flip=False):
		super(Dataset_def, self).__init__(infos, train=train)
		self.data_rgb = Dataset_RGB(infos, train=train, transform=transform_rgb)
		self.data_of = Dataset_OF(infos, train=train, transform=transform_of, num_frames=num_frames,
			remove_motion=remove_motion, cutout_center=cutout_center, time_flip=False)
		self.num_frames = num_frames
		self.high_motion = high_motion
		self.time_flip = time_flip

	def __getitem__(self, index_big):
		index_big = self._prep_index(index_big)
		info, index = self.get_info_index(index_big)
		num_rgb = info.get_num_rgb(index)
		random = np.random.RandomState()
		list_mag = info.get_mag(index)
		ind_frame_first = sample_high_motion(list_mag, self.num_frames, mode=self.high_motion)
		first, _ = self.data_rgb[index_big, ind_frame_first]
		last, _ = self.data_rgb[index_big, ind_frame_first+self.num_frames]
		flow, _ = self.data_of[index_big, ind_frame_first]
		flow_negatives = []
		indices = random.randint(0, len(self), size=2)
		for index_big in indices:
			info, index = self.get_info_index(index_big)
			num_rgb = info.get_num_rgb(index)
			list_mag = info.get_mag(index)
			ind_frame_first = sample_high_motion(list_mag, self.num_frames, mode=self.high_motion)
			flow_negative, _ = self.data_of[index_big, ind_frame_first]
			flow_negatives.append(flow_negative)
		return first, last, flow, flow_negatives[0], flow_negatives[1]

	def preprocess(self, raw):
		raw = list(raw)
		random = np.random.RandomState()
		randomstate = random.get_state() 
		rand_flip = 0
		if self.time_flip and self.train:
			rand_flip = np.random.rand()
		first, last, flow, flow_n1, flow_n2 = raw
		first, _ = self.data_rgb.preprocess((first, None, random))
		random.set_state(randomstate)
		last, _ = self.data_rgb.preprocess((last, None, random))
		random.set_state(randomstate)
		flow, _ = self.data_of.preprocess((flow, None, random))
		flow_n1, _ = self.data_of.preprocess((flow_n1, None, random))
		flow_n2, _ = self.data_of.preprocess((flow_n2, None, random))
		flow = rand_timeflip(flow, rand_flip, 2)
		if rand_flip > 0.5:
			temp = first
			first = last
			last = temp
		if self.time_flip and self.train:
			rand_flip_1 = np.random.rand()
			rand_flip_2 = np.random.rand()
			flow_n1 = rand_timeflip(flow_n1, rand_flip_1, 2)
			flow_n2 = rand_timeflip(flow_n2, rand_flip_2, 2)
		return first, last, flow, flow_n1, flow_n2

	@property
	def data_cache(self):
		return [self.data_rgb.data_cache, self.data_of.data_cache]

	@data_cache.setter
	def data_cache(self, cache):
		self.data_rgb.data_cache = cache[0]
		self.data_of.data_cache = cache[1]		


class Dataset_fm(Base_Dataset):
	def __init__(self, infos, train=True, transform_rgb=None, transform_of=None, transform_cod=None,
		num_frames=12, num_frames_cod=4, max_shift=0, remove_motion=False, cutout_center=0,
		modalities = ['rgb', 'of'], high_motion=False, time_flip=False):
		super(Dataset_fm, self).__init__(infos, train=train)
		self.num_frames = num_frames
		self.num_frames_cod = num_frames_cod
		self.max_shift = max_shift
		self.modalities = modalities
		self.high_motion = high_motion
		self.time_flip = time_flip
		if num_frames_cod > num_frames:
			raise Exception('num_frames must be bigger than num_frames_cod')
		if 'rgb' in modalities:
			self.data_rgb = Dataset_RGB(infos, train=train, transform=transform_rgb)
		if 'of' in modalities:
			self.data_of = Dataset_OF(infos, train=train, transform=transform_of, num_frames=num_frames, 
				remove_motion=remove_motion, cutout_center=cutout_center, time_flip=False)
		if 'cod' in modalities:
			self.data_cod = Dataset_COD(infos, train=train, transform=transform_cod, 
				num_frames=num_frames_cod, cutout_center=cutout_center, time_flip=False)

	def __getitem__(self, index_big_positive):
		index_big_positive = self._prep_index(index_big_positive)
		random = np.random.RandomState()
		index_big_negative = random.randint(0, len(self))
		raw = []
		for index_big in [index_big_positive, index_big_negative]:
			info, index = self.get_info_index(index_big)
			num_rgb = info.get_num_rgb(index)
			list_mag = info.get_mag(index)
			ind_frame_first = sample_high_motion(list_mag, self.num_frames, mode=self.high_motion)
			ind_frame_center = ind_frame_first + int(self.num_frames/2)
			if 'rgb' in self.modalities:
				ind_frame_image = random.randint(np.max([0, ind_frame_center-self.max_shift]), 
					np.min([ind_frame_center+self.max_shift+1, num_rgb]))
				image, _ = self.data_rgb[index_big, ind_frame_image]
				raw.append(image)
				if 'rgb2' in self.modalities:
					raw.append(image)
			if 'of' in self.modalities:
				ind_frame_first = ind_frame_center - int(self.num_frames/2)
				flow, _ = self.data_of[index_big, ind_frame_first]
				raw.append(flow)
			if 'cod' in self.modalities:
				ind_frame_first = ind_frame_center - int(self.num_frames_cod/2)
				cod, _ = self.data_cod[index_big, ind_frame_first]			
				raw.append(cod)
		return raw

	def preprocess(self, raw):
		raw = list(raw)
		samples = []
		rand_flip = 0
		if self.time_flip and self.train:
			rand_flip = np.random.rand()
		for i in range(2):
			random = np.random.RandomState()
			randomstate = random.get_state() 
			if 'rgb' in self.modalities:
				random.set_state(randomstate)
				image = raw.pop(0)
				image, _ = self.data_rgb.preprocess((image, None, random))
				samples.append(image)
				#if 'rgb2' in self.modalities:
				#	samples.append(image)
			if 'of' in self.modalities:
				random.set_state(randomstate)
				flow = raw.pop(0)
				flow, _ = self.data_of.preprocess((flow, None, random))
				flow = rand_timeflip(flow, rand_flip, 2)
				samples.append(flow)
			if 'cod' in self.modalities:
				random.set_state(randomstate)
				cod = raw.pop(0)
				cod, _ = self.data_cod.preprocess((cod, None, random))
				cod = rand_timeflip(cod, rand_flip, 3)
				samples.append(cod)
			if 'rgb2' in self.modalities:
				random.set_state(randomstate)
				image = raw.pop(0)
				image, _ = self.data_rgb.preprocess((image, None, random))
				samples.append(image)
		return samples
		# image, flow, flow_negative = raw
		# image, _ = self.data_rgb.preprocess((image, None, random))
		# random.set_state(randomstate)
		# flow, _ = self.data_of.preprocess((flow, None, random))
		# flow_negative, _ = self.data_of.preprocess((flow_negative, None, random))
		# return image, flow, flow_negative

	@property
	def data_cache(self):
		data_caches = []
		if 'rgb' in self.modalities:
			data_caches.append(self.data_rgb.data_cache)
		if 'of' in self.modalities:
			data_caches.append(self.data_of.data_cache)
		if 'cod' in self.modalities:
			data_caches.append(self.data_cod.data_cache)
		return data_caches

	@data_cache.setter
	def data_cache(self, data_caches):
		if 'rgb' in self.modalities:
			data_cache = data_caches.pop(0)
			self.data_rgb.data_cache = data_cache
		if 'of' in self.modalities:
			data_cache = data_caches.pop(0)
			self.data_of.data_cache = data_cache
		if 'cod' in self.modalities:
			data_cache = data_caches.pop(0)
			self.data_cod.data_cache = data_cache	

class Dataset_sl(Base_Dataset):
	def __init__(self, infos, train=True, transform_rgb=None, num_frames=20, min_spacing=3,
		high_motion=False, time_flip=False, same_video=True, max_spacing=10, min_msd=0):
		super(Dataset_sl, self).__init__(infos, train=train)
		self.data_rgb = Dataset_RGB(infos, train=train, transform=transform_rgb)
		self.num_frames = num_frames
		self.min_spacing = min_spacing
		self.high_motion = high_motion
		self.time_flip = time_flip
		self.same_video = same_video
		self.max_spacing = max_spacing
		self.min_msd = min_msd

	def __getitem__(self, index_big):
		index_big = self._prep_index(index_big)
		info, index = self.get_info_index(index_big)
		num_rgb = info.get_num_rgb(index)
		random = np.random.RandomState()
		list_mag = info.get_mag(index)
		ind_frame_first = sample_high_motion(list_mag, 2, mode=self.high_motion)
		ind_frame_first += 1
		msd = info.get_msd(index, ind_frame_first)
		indices_frame = self.sample_indices(ind_frame_first, num_rgb, msd)
		# indices_frame = sample_indices(self.num_frames, self.min_spacing) + ind_frame_first
		indices_big = [index_big] * 5
		# if not self.same_video:
		# 	index_big_neg = random.randint(0, len(self))
		# 	info, index = self.get_info_index(index_big_neg)
		# 	num_rgb = info.get_num_rgb(index)
		# 	ind_frame_first = random.randint(0, num_rgb-self.num_frames)
		# 	indices_frame_neg = sample_indices(self.num_frames, self.min_spacing) + ind_frame_first
		# 	indices_frame[0] = indices_frame_neg[0]
		# 	indices_frame[4] = indices_frame_neg[4]
		# 	indices_big[0] = index_big_neg
		# 	indices_big[4] = index_big_neg
		images = []
		for i in range(5):
			index_big, ind_frame = indices_big[i], indices_frame[i]
			image, _ = self.data_rgb[index_big, ind_frame]
			images.append(image)
		return images

	def sample_indices(self, ind_frame, num_rgb, msd):
		lower = np.random.randint(np.max([0, ind_frame-self.max_spacing]), ind_frame)
		upper = np.random.randint(ind_frame+1, np.min([num_rgb, ind_frame+self.max_spacing+1]))
		msd[lower:upper+1] = 0
		indices_sorted = np.argsort(msd)
		start = -3
		while msd[indices_sorted[start-1]] > self.min_msd:
			start -= 1
		possible_indices = indices_sorted[start:]
		np.random.shuffle(possible_indices)
		indices = np.array([possible_indices[0], lower, ind_frame, upper, 
			possible_indices[1]])
		return indices

	def preprocess(self, raw):
		raw = list(raw)
		random = np.random.RandomState()
		randomstate = random.get_state() 
		rand_flip = 0
		if self.time_flip and self.train:
			rand_flip = np.random.rand()
		if rand_flip > 0.5:
			raw.reverse()
		images = []
		for image in raw:
			random.set_state(randomstate)
			image, _ = self.data_rgb.preprocess((image, None, random))
			images.append(image)
		return images

	@property
	def data_cache(self):
		return [self.data_rgb.data_cache]

	@data_cache.setter
	def data_cache(self, cache):
		self.data_rgb.data_cache = cache[0]	

if __name__ == '__main__':
	from compvis.datasets import OlympicSports_i, UCF101_i, HMDB51_i, ACT_i
	from compvis import transforms_det as transforms 

	# transform_rgb = transforms.Compose([
	# 	transforms.Scale(256), 
	# 	transforms.RandomCrop(224),
	# 	transforms.RandomHorizontalFlip(), 
	# 	transforms.ToTensor()])
	# transform_of = transforms.Compose([
	# 	transforms.Scale(256), 
	# 	transforms.RandomCrop(224),
	# 	transforms.RandomHorizontalFlip(), 
	# 	transforms.ToTensor(), 
	# 	transforms.SubMeanDisplacement()])
	# transform_cod = transforms.Compose([
	# 	transforms.Scale(256), 
	# 	transforms.RandomCrop(224),
	# 	transforms.RandomHorizontalFlip(), 
	# 	transforms.ToTensor()])

	# num_frames = 60
	# min_msd = 2000

	# info = [
	# 	UCF101_i(num_frames=num_frames, min_msd=min_msd),
	# 	HMDB51_i(num_frames=num_frames, min_msd=min_msd),
	# 	ACT_i(num_frames=num_frames, min_msd=min_msd)
	# 	]
	# dataset = Dataset_sl(info)
	# print(len(dataset))
	# raw = dataset[0]


	for i in range(100):
		list_mag = np.random.uniform(0,10, size=5)
		ind = sample_high_motion(list_mag, 3)
		print(ind)


	# def __getitem__(self, index_big):
	# 	info, index = self.get_info_index(index_big)
	# 	num_rgb = info.get_num_rgb(index)
	# 	random = np.random.RandomState()
	# 	ind_frames_first = np.array([random.randint(0, num_rgb-self.num_frames)]).astype(np.int32)
	# 	sample = []
	# 	if self.modalities != 3:
	# 		ind_frames_first_image = []
	# 		for iff in ind_frames_first:
	# 			iff += int(self.num_frames / 2)
	# 			iffi = random.randint(np.max([0, iff-self.max_shift]), np.min([iff+self.max_shift+1,num_rgb]))
	# 			ind_frames_first_image.append(iffi)
	# 		ind_frames_first_image = np.array(ind_frames_first_image).astype(np.int32)
	# 		image, _ = self.data_rgb[index_big, ind_frames_first_image]
	# 		sample.append(image)
	# 	if self.modalities != 1:
	# 		cod, _ = self.data_cod[index_big, ind_frames_first]
	# 		if self.modalities == 3:
	# 			sample.append(cod)
	# 		else:
	# 			if not self.hard:
	# 				index_big = random.randint(0, len(self))
	# 				info, index = self.get_info_index(index_big)
	# 				num_rgb = info.get_num_rgb(index)
	# 			ind_frames_first = np.array([random.randint(0, num_rgb-self.num_frames)]).astype(np.int32)
	# 			cod_negative, _ = self.data_cod[index_big, ind_frames_first]
	# 			sample.append(cod, cod_negative)
	# 	if self.modalities != 2:	
	# 		flow, _ = self.data_of[index_big, ind_frames_first]
	# 		if not self.hard:
	# 			index_big = random.randint(0, len(self))
	# 			info, index = self.get_info_index(index_big)
	# 			num_rgb = info.get_num_rgb(index)
	# 		ind_frames_first = np.array([random.randint(0, num_rgb-self.num_frames)]).astype(np.int32)
	# 		flow_negative, _ = self.data_of[index_big, ind_frames_first]
	# 		sample.append(flow, flow_negative)
	# 	return sample[0], sample[1], sample[2]